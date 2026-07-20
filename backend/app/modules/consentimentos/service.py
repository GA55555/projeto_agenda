"""Regras de negocio de consentimentos (TCLE). Nenhum acesso cross-tenant (§2.1).

A revogacao seta `revogado_em`/`revogado_por_usuario_id` e grava um registro
INDELEVEL em `auditoria` — na MESMA transacao (atomico). O registro imutavel da
revogacao e a linha de auditoria, nao o UPDATE em si (§2.2).

Regras de ouro: §2.1, §2.2
Fase do roadmap: Fase 3
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit import service as audit_service
from app.modules.audit.models import TIPO_CONSENTIMENTO_REVOGADO
from app.modules.auth.dependencies import CurrentUser
from app.modules.consentimentos.exceptions import ConsentimentoJaRevogado
from app.modules.consentimentos.models import Consentimento


def listar_por_paciente(db: Session, paciente_id: uuid.UUID) -> list[Consentimento]:
    stmt = (
        select(Consentimento)
        .where(Consentimento.paciente_id == paciente_id)
        .order_by(Consentimento.concedido_em.desc())
    )
    return list(db.execute(stmt).scalars())


def obter(db: Session, consentimento_id: uuid.UUID) -> Consentimento | None:
    return db.get(Consentimento, consentimento_id)


def clausula_consentimento_ativo(paciente_id_ref):
    """Predicado EXISTS "paciente tem >=1 TCLE nao revogado" (§2.2).

    FONTE UNICA da definicao de "consentimento vigente". `paciente_id_ref` pode
    ser um valor (uuid) ou uma coluna (ex.: `Paciente.id`, para agregacoes como
    o dashboard) — assim gate e contadores nunca divergem se a definicao mudar
    (ex.: ganhar validade/expiracao).
    """
    return (
        select(Consentimento.id)
        .where(Consentimento.paciente_id == paciente_id_ref)
        .where(Consentimento.revogado_em.is_(None))
        .exists()
    )


def tem_consentimento_ativo(db: Session, paciente_id: uuid.UUID) -> bool:
    """True se o paciente tem >=1 TCLE nao revogado (§2.2).

    Fonte unica do gate de consentimento — usado por quem processa/grava dados
    clinicos do paciente (evolucoes, geracao via LLM). Roda sob RLS (§2.1).
    """
    return bool(db.execute(select(clausula_consentimento_ativo(paciente_id))).scalar())


def revogar(
    db: Session, user: CurrentUser, consentimento_id: uuid.UUID, motivo: str | None
) -> Consentimento | None:
    consentimento = db.get(Consentimento, consentimento_id)
    if consentimento is None:
        return None
    if consentimento.revogado_em is not None:
        raise ConsentimentoJaRevogado(str(consentimento_id))

    consentimento.revogado_em = datetime.now(timezone.utc)
    consentimento.revogado_por_usuario_id = user.id
    db.flush()

    audit_service.registrar_evento(
        db,
        tenant_id=user.tenant_id,
        tipo_evento=TIPO_CONSENTIMENTO_REVOGADO,
        entidade="consentimento",
        entidade_id=consentimento.id,
        ator_usuario_id=user.id,
        payload={
            "paciente_id": str(consentimento.paciente_id),
            "responsavel_id": str(consentimento.responsavel_id),
            "motivo": motivo,
        },
    )
    return consentimento
