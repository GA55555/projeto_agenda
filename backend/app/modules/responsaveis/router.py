"""Rotas de responsaveis legais. Todas sob `get_tenant_session` (RLS ativo, §2.1).

Regras de ouro: §2.1, §2.2
Fase do roadmap: Fase 3
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.auth.dependencies import CurrentUser, get_current_user
from app.modules.responsaveis import service
from app.modules.responsaveis.exceptions import CpfDuplicado
from app.modules.responsaveis.schemas import (
    ResponsavelCreate,
    ResponsavelListaOut,
    ResponsavelOut,
    ResponsavelUpdate,
)

router = APIRouter(prefix="/responsaveis", tags=["responsaveis"])


@router.post("", response_model=ResponsavelOut, status_code=status.HTTP_201_CREATED)
def criar_responsavel(
    dados: ResponsavelCreate,
    db: Session = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> ResponsavelOut:
    try:
        return service.criar(db, user.tenant_id, dados)
    except CpfDuplicado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ja existe um responsavel com este CPF neste tenant.",
        )


@router.get("", response_model=list[ResponsavelListaOut])
def listar_responsaveis(db: Session = Depends(get_tenant_session)) -> list[ResponsavelListaOut]:
    return service.listar(db)


@router.get("/{responsavel_id}", response_model=ResponsavelOut)
def obter_responsavel(
    responsavel_id: uuid.UUID, db: Session = Depends(get_tenant_session)
) -> ResponsavelOut:
    resp = service.obter(db, responsavel_id)
    if resp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Responsavel nao encontrado")
    return resp


@router.patch("/{responsavel_id}", response_model=ResponsavelOut)
def atualizar_responsavel(
    responsavel_id: uuid.UUID,
    dados: ResponsavelUpdate,
    db: Session = Depends(get_tenant_session),
) -> ResponsavelOut:
    resp = service.atualizar(db, responsavel_id, dados)
    if resp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Responsavel nao encontrado")
    return resp
