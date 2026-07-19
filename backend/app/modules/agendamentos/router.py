"""Rotas de agendamentos. Todas sob `get_tenant_session` (RLS ativo, §2.1).

Sobreposicao de horario -> 409 (barrada pelo EXCLUDE no BD, §2.1).
Paciente inexistente no tenant -> 422.

Regras de ouro: §2.1
Fase do roadmap: Fase 3.5
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.agendamentos import service
from app.modules.agendamentos.exceptions import (
    HorarioIndisponivel,
    IntervaloInvalido,
    PacienteInexistente,
)
from app.modules.agendamentos.schemas import (
    AgendamentoCreate,
    AgendamentoOut,
    AgendamentoUpdate,
    CancelamentoIn,
)
from app.modules.auth.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/agendamentos", tags=["agendamentos"])

_CONFLITO_HORARIO = "Conflito de horario: sobreposicao com outro atendimento"


@router.post("", response_model=AgendamentoOut, status_code=status.HTTP_201_CREATED)
def criar_agendamento(
    dados: AgendamentoCreate,
    db: Session = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> AgendamentoOut:
    try:
        return service.criar(db, user.tenant_id, dados)
    except PacienteInexistente as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Paciente inexistente no tenant: {exc}",
        )
    except HorarioIndisponivel:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_CONFLITO_HORARIO)


@router.get("", response_model=list[AgendamentoOut])
def listar_agendamentos(
    de: datetime | None = None,
    ate: datetime | None = None,
    paciente_id: uuid.UUID | None = None,
    status_: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_tenant_session),
) -> list[AgendamentoOut]:
    return service.listar(db, de=de, ate=ate, paciente_id=paciente_id, status=status_)


@router.get("/{agendamento_id}", response_model=AgendamentoOut)
def obter_agendamento(
    agendamento_id: uuid.UUID, db: Session = Depends(get_tenant_session)
) -> AgendamentoOut:
    ag = service.obter(db, agendamento_id)
    if ag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agendamento nao encontrado")
    return ag


@router.patch("/{agendamento_id}", response_model=AgendamentoOut)
def atualizar_agendamento(
    agendamento_id: uuid.UUID,
    dados: AgendamentoUpdate,
    db: Session = Depends(get_tenant_session),
) -> AgendamentoOut:
    try:
        ag = service.atualizar(db, agendamento_id, dados)
    except IntervaloInvalido:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fim deve ser posterior a inicio",
        )
    except HorarioIndisponivel:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_CONFLITO_HORARIO)
    if ag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agendamento nao encontrado")
    return ag


@router.post("/{agendamento_id}/cancelar", response_model=AgendamentoOut)
def cancelar_agendamento(
    agendamento_id: uuid.UUID,
    dados: CancelamentoIn,
    db: Session = Depends(get_tenant_session),
) -> AgendamentoOut:
    ag = service.cancelar(db, agendamento_id, dados.motivo)
    if ag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agendamento nao encontrado")
    return ag
