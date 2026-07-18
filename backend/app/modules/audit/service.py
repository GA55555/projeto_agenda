"""Escrita/leitura da auditoria imutavel (§2.2).

`registrar_evento` e chamado DENTRO da mesma transacao do evento de dominio
(ex.: revogacao de consentimento) — se o dominio falha, o log some junto
(atomico). A imutabilidade (nao poder alterar/apagar depois do commit) e
imposta no BD (grants + trigger), nao aqui.

Regras de ouro: §2.1, §2.2
Fase do roadmap: Fase 3
"""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.models import Auditoria


def registrar_evento(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    tipo_evento: str,
    entidade: str,
    entidade_id: uuid.UUID,
    ator_usuario_id: uuid.UUID,
    payload: dict[str, Any] | None = None,
) -> Auditoria:
    evento = Auditoria(
        tenant_id=tenant_id,
        tipo_evento=tipo_evento,
        entidade=entidade,
        entidade_id=entidade_id,
        ator_usuario_id=ator_usuario_id,
        payload=payload or {},
    )
    db.add(evento)
    db.flush()
    return evento


def listar(
    db: Session,
    *,
    entidade: str | None = None,
    tipo_evento: str | None = None,
    limit: int = 100,
) -> list[Auditoria]:
    """Lista eventos do tenant ativo (RLS), mais recentes primeiro."""
    stmt = select(Auditoria).order_by(Auditoria.criado_em.desc())
    if entidade is not None:
        stmt = stmt.where(Auditoria.entidade == entidade)
    if tipo_evento is not None:
        stmt = stmt.where(Auditoria.tipo_evento == tipo_evento)
    return list(db.execute(stmt.limit(limit)).scalars())
