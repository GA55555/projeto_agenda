"""Rotas do dashboard. Sob `get_tenant_session` (RLS ativo, §2.1).

Dia e mes sao endpoints separados (Fase 7f): o calendario troca o dia sem
recomputar as agregacoes do mes/pacientes.

Regras de ouro: §2.1
Fase do roadmap: Fase 7c/7e/7f/7j
"""
import uuid
from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.auth.dependencies import get_current_user
from app.modules.dashboard import service
from app.modules.dashboard.schemas import PacienteSessoesResumo, ResumoDia, ResumoMes

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/dia", response_model=ResumoDia)
def resumo_dia(
    dia: date | None = None,
    db: Session = Depends(get_tenant_session),
    _=Depends(get_current_user),
) -> ResumoDia:
    """Contadores do dia (YYYY-MM-DD; omitido = hoje no fuso da clinica)."""
    return service.montar_resumo_dia(db, dia=dia)


@router.get("/mes", response_model=ResumoMes)
def resumo_mes(
    mes: str | None = None,
    db: Session = Depends(get_tenant_session),
    _=Depends(get_current_user),
) -> ResumoMes:
    """Estado atual + estatisticas do mes + pendencias (YYYY-MM; omitido = mes atual)."""
    try:
        return service.montar_resumo_mes(db, mes=mes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/calendario", response_model=dict[str, int])
def calendario(
    mes: str | None = None,
    db: Session = Depends(get_tenant_session),
    _=Depends(get_current_user),
) -> dict[str, int]:
    """Mapa dia->contagem de atendimentos do mes (YYYY-MM; omitido = mes atual)."""
    try:
        return service.calendario_do_mes(db, mes=mes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/pacientes/{paciente_id}/sessoes", response_model=PacienteSessoesResumo)
def resumo_sessoes_paciente(
    paciente_id: uuid.UUID,
    de: datetime | None = None,
    ate: datetime | None = None,
    status_sessao: Literal["agendado", "realizado", "cancelado", "falta"] | None = Query(
        default=None, alias="status"
    ),
    limite: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_tenant_session),
    _=Depends(get_current_user),
) -> PacienteSessoesResumo:
    if de is not None and ate is not None and ate <= de:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ate deve ser posterior a de",
        )
    resumo = service.montar_resumo_sessoes_paciente(
        db,
        paciente_id,
        de=de,
        ate=ate,
        status=status_sessao,
        limite=limite,
        offset=offset,
    )
    if resumo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente nao encontrado")
    return resumo
