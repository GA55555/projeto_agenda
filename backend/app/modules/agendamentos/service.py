"""Regras de negocio de agendamentos. Nenhum acesso cross-tenant (§2.1).

O RLS restringe SELECT/UPDATE ao tenant ativo; no INSERT o `tenant_id` e setado
explicitamente. A nao-sobreposicao e imposta no BD (EXCLUDE); aqui apenas
traduzimos a violacao (SQLSTATE 23P01) em `HorarioIndisponivel` -> 409.

Regras de ouro: §2.1
Fase do roadmap: Fase 3.5
"""
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.agendamentos.exceptions import (
    HorarioIndisponivel,
    IntervaloInvalido,
    PacienteInexistente,
    TransicaoInvalida,
)
from app.modules.agendamentos.models import STATUS_AGENDADO, STATUS_CANCELADO, Agendamento
from app.modules.agendamentos.schemas import AgendamentoCreate, AgendamentoUpdate
from app.modules.pacientes.models import Paciente

# exclusion_violation — sobreposicao barrada pela constraint EXCLUDE.
_EXCLUSION_VIOLATION = "23P01"


def validar_transicao_status(atual: str, novo: str) -> None:
    """Maquina de estados do agendamento no BACKEND (Fase 7c), nao so na UI.

    Regras: `cancelado` e TERMINAL e so se entra nele pela rota /cancelar (que
    carrega o motivo e a semantica soft) — o PATCH nao entra nem sai de
    cancelado. Entre agendado/realizado/falta a transicao e livre (correcao de
    apontamento e legitima). No-op (novo == atual) e permitido.

    Sem isto, um PATCH direto faria cancelado->realizado (registro 'realizado'
    com motivo_cancelamento preenchido) e corromperia os agregados do dashboard.
    """
    if novo == atual:
        return
    if atual == STATUS_CANCELADO:
        raise TransicaoInvalida("agendamento cancelado e terminal; crie um novo")
    if novo == STATUS_CANCELADO:
        raise TransicaoInvalida("para cancelar, use a rota de cancelamento")


def _flush_traduzindo(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) == _EXCLUSION_VIOLATION:
            raise HorarioIndisponivel() from exc
        raise


def _paciente_existe(db: Session, paciente_id: uuid.UUID) -> bool:
    # RLS: so encontra se o paciente for do tenant ativo.
    stmt = select(Paciente.id).where(Paciente.id == paciente_id)
    return db.execute(stmt).scalar_one_or_none() is not None


def criar(db: Session, tenant_id: uuid.UUID, dados: AgendamentoCreate) -> Agendamento:
    if not _paciente_existe(db, dados.paciente_id):
        raise PacienteInexistente(str(dados.paciente_id))
    ag = Agendamento(
        tenant_id=tenant_id,
        paciente_id=dados.paciente_id,
        inicio=dados.inicio,
        fim=dados.fim,
        tipo=dados.tipo,
        observacao=dados.observacao,
    )
    db.add(ag)
    _flush_traduzindo(db)
    return ag


def listar(
    db: Session,
    *,
    de: datetime | None = None,
    ate: datetime | None = None,
    paciente_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[Agendamento]:
    stmt = select(Agendamento).order_by(Agendamento.inicio)
    if de is not None:
        stmt = stmt.where(Agendamento.inicio >= de)
    if ate is not None:
        stmt = stmt.where(Agendamento.inicio < ate)
    if paciente_id is not None:
        stmt = stmt.where(Agendamento.paciente_id == paciente_id)
    if status is not None:
        stmt = stmt.where(Agendamento.status == status)
    return list(db.execute(stmt).scalars())


def obter(db: Session, agendamento_id: uuid.UUID) -> Agendamento | None:
    return db.get(Agendamento, agendamento_id)


def atualizar(
    db: Session, agendamento_id: uuid.UUID, dados: AgendamentoUpdate
) -> Agendamento | None:
    ag = db.get(Agendamento, agendamento_id)
    if ag is None:
        return None
    campos = dados.model_dump(exclude_unset=True)
    if "status" in campos:
        validar_transicao_status(ag.status, campos["status"])
    for campo, valor in campos.items():
        setattr(ag, campo, valor)
    # Update parcial: valida o intervalo EFETIVO (novo + valores atuais) antes do
    # flush, para dar 422 em vez de estourar o CHECK do BD como 500.
    if ag.fim <= ag.inicio:
        raise IntervaloInvalido()
    _flush_traduzindo(db)  # reagendamento tambem passa pelo EXCLUDE
    return ag


def cancelar(
    db: Session, agendamento_id: uuid.UUID, motivo: str | None
) -> Agendamento | None:
    ag = db.get(Agendamento, agendamento_id)
    if ag is None:
        return None
    # So se cancela o que esta AGENDADO: re-cancelar sobrescreveria o motivo
    # original (historico que o soft-cancel existe para preservar) e cancelar
    # um realizado/falta apagaria um apontamento ja feito.
    if ag.status != STATUS_AGENDADO:
        raise TransicaoInvalida(f"nao e possivel cancelar um agendamento '{ag.status}'")
    ag.status = STATUS_CANCELADO
    ag.motivo_cancelamento = motivo
    db.flush()  # cancelar libera o horario (fica fora do EXCLUDE)
    return ag
