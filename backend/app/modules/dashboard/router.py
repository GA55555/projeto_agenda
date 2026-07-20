"""Rota do resumo do dashboard. Sob `get_tenant_session` (RLS ativo, §2.1).

Regras de ouro: §2.1
Fase do roadmap: Fase 7c/7e
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.auth.dependencies import get_current_user
from app.modules.dashboard import service
from app.modules.dashboard.schemas import ResumoDashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/resumo", response_model=ResumoDashboard)
def resumo(
    dia: date | None = None,
    mes: str | None = None,
    db: Session = Depends(get_tenant_session),
    _=Depends(get_current_user),
) -> ResumoDashboard:
    """Indicadores agregados da clinica.

    `dia` (YYYY-MM-DD) e `mes` (YYYY-MM) selecionam o periodo historico;
    omitidos, valem hoje/mes atual (fuso da clinica). Pendencias sao sempre
    relativas a agora.
    """
    try:
        return service.montar_resumo(db, dia=dia, mes=mes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
