"""Rotas de pacientes. Todas sob `get_tenant_session` (RLS ativo, §2.1).

`POST /pacientes` cria paciente + vinculos + TCLE atomicamente (invariante §2.2).

Regras de ouro: §2.1, §2.2
Fase do roadmap: Fase 3
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.auth.dependencies import CurrentUser, get_current_user
from app.modules.pacientes import service
from app.modules.pacientes.exceptions import (
    PacienteComAgendamentosFuturos,
    PacienteComProntuario,
    ResponsavelInexistente,
)
from app.modules.pacientes.schemas import (
    ArquivarPacienteIn,
    PacienteCreate,
    PacienteDetalhado,
    PacienteOut,
    PacienteUpdate,
)

router = APIRouter(prefix="/pacientes", tags=["pacientes"])


@router.post("", response_model=PacienteDetalhado, status_code=status.HTTP_201_CREATED)
def criar_paciente(
    dados: PacienteCreate,
    db: Session = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> PacienteDetalhado:
    try:
        return service.criar_paciente(db, user, dados)
    except ResponsavelInexistente as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Responsavel(is) inexistente(s) no tenant: {exc}",
        )


@router.get("", response_model=list[PacienteOut])
def listar_pacientes(
    ativo: bool | None = None,
    db: Session = Depends(get_tenant_session),
) -> list[PacienteOut]:
    return service.listar(db, ativo=ativo)


@router.get("/{paciente_id}", response_model=PacienteDetalhado)
def obter_paciente(
    paciente_id: uuid.UUID, db: Session = Depends(get_tenant_session)
) -> PacienteDetalhado:
    paciente = service.obter(db, paciente_id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente nao encontrado")
    return paciente


@router.post("/{paciente_id}/arquivar", response_model=PacienteOut)
def arquivar_paciente(
    paciente_id: uuid.UUID,
    dados: ArquivarPacienteIn,
    db: Session = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> PacienteOut:
    try:
        paciente = service.arquivar(db, user, paciente_id, dados.motivo)
    except PacienteComAgendamentosFuturos as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Resolva os {exc.quantidade} agendamento(s) futuro(s) antes de arquivar."
            ),
        )
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente nao encontrado")
    return paciente


@router.post("/{paciente_id}/reativar", response_model=PacienteOut)
def reativar_paciente(
    paciente_id: uuid.UUID,
    db: Session = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> PacienteOut:
    paciente = service.reativar(db, user, paciente_id)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente nao encontrado")
    return paciente


@router.patch("/{paciente_id}", response_model=PacienteOut)
def atualizar_paciente(
    paciente_id: uuid.UUID,
    dados: PacienteUpdate,
    db: Session = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> PacienteOut:
    paciente = service.atualizar(db, user, paciente_id, dados)
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente nao encontrado")
    return paciente


@router.delete("/{paciente_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_paciente(
    paciente_id: uuid.UUID,
    db: Session = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> None:
    """Exclusao definitiva — so cadastro SEM prontuario (CFP 001/2009, §0.3)."""
    try:
        encontrado = service.apagar_paciente(db, user, paciente_id)
    except PacienteComProntuario:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Paciente possui prontuario (evolucoes ou documentos): a exclusao e bloqueada "
                "pela guarda obrigatoria de 5 anos (CFP 001/2009). Use o arquivamento."
            ),
        )
    if not encontrado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente nao encontrado")
