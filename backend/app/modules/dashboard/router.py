"""Rota do resumo do dashboard. Sob `get_tenant_session` (RLS ativo, §2.1).

Regras de ouro: §2.1
Fase do roadmap: Fase 7c
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.auth.dependencies import get_current_user
from app.modules.dashboard import service
from app.modules.dashboard.schemas import ResumoDashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/resumo", response_model=ResumoDashboard)
def resumo(
    db: Session = Depends(get_tenant_session),
    _=Depends(get_current_user),
) -> ResumoDashboard:
    """Indicadores agregados da clinica (hoje, mes e pendencias)."""
    return service.montar_resumo(db)
