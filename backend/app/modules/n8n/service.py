"""Outbox + HMAC do webhook n8n.

O evento nasce na mesma transacao da assinatura. A rede e tocada somente por
`despachar`, numa requisicao posterior ao commit (§4.2).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.evolucoes.models import Evolucao
from app.modules.n8n.models import N8nOutbox

logger = logging.getLogger(__name__)


def enfileirar(db: Session, *, tenant_id: uuid.UUID, evolucao_id: uuid.UUID) -> N8nOutbox:
    evento = N8nOutbox(tenant_id=tenant_id, evolucao_id=evolucao_id)
    db.add(evento)
    db.flush()
    return evento


def corpo_canonico(payload: dict) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def assinatura_hmac(*, secret: str, timestamp: str, evento_id: uuid.UUID, body: bytes) -> str:
    mensagem = timestamp.encode() + b"." + str(evento_id).encode() + b"." + body
    return "sha256=" + hmac.new(secret.encode(), mensagem, hashlib.sha256).hexdigest()


def despachar(db: Session, evento_id: uuid.UUID) -> bool:
    evento = db.scalar(
        select(N8nOutbox).where(N8nOutbox.id == evento_id).with_for_update()
    )
    if evento is None:
        return False
    if evento.estado == "enviado":
        return True
    if not settings.n8n_webhook_url or not settings.n8n_webhook_secret:
        evento.ultimo_erro = "configuracao_ausente"
        return False

    evolucao = db.get(Evolucao, evento.evolucao_id)
    if evolucao is None:  # FK RESTRICT; defesa adicional fail-closed
        evento.ultimo_erro = "evolucao_inexistente"
        return False

    payload = {
        "evento_id": str(evento.id),
        "tipo": "evolucao_assinada",
        "evolucao_id": str(evolucao.id),
        "assinada_em": evolucao.assinada_em.isoformat(),
        "texto": evolucao.texto,
    }
    body = corpo_canonico(payload)
    agora = datetime.now(UTC)
    timestamp = str(int(agora.timestamp()))
    headers = {
        "Content-Type": "application/json",
        "X-Agenda-Event-Id": str(evento.id),
        "X-Agenda-Timestamp": timestamp,
        "X-Agenda-Signature": assinatura_hmac(
            secret=settings.n8n_webhook_secret,
            timestamp=timestamp,
            evento_id=evento.id,
            body=body,
        ),
    }
    evento.tentativas += 1
    evento.ultima_tentativa_em = agora
    try:
        response = httpx.post(
            settings.n8n_webhook_url,
            content=body,
            headers=headers,
            timeout=settings.n8n_webhook_timeout_seconds,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        evento.ultimo_erro = type(exc).__name__[:80]
        logger.warning("n8n indisponivel; evento=%s tentativa=%d", evento.id, evento.tentativas)
        return False
    evento.estado = "enviado"
    evento.enviado_em = datetime.now(UTC)
    evento.ultimo_erro = None
    logger.info("evento n8n entregue; evento=%s", evento.id)
    return True


def despachar_pendentes(db: Session, *, limite: int = 5) -> tuple[int, int]:
    """Tenta poucos eventos do tenant; falha de rede nunca desfaz a assinatura."""
    ids = list(
        db.scalars(
            select(N8nOutbox.id)
            .where(N8nOutbox.estado == "pendente")
            .order_by(N8nOutbox.criado_em)
            .limit(limite)
        )
    )
    enviados = sum(1 for evento_id in ids if despachar(db, evento_id))
    return enviados, len(ids) - enviados
