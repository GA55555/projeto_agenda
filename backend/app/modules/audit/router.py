"""Rotas de auditoria (append-only, somente leitura) — §2.2.

Sob `get_tenant_session` (RLS ativo). Nao ha POST/PATCH/DELETE: a auditoria e
escrita internamente pelos servicos de dominio e e imutavel no BD (§2.2).

Regras de ouro: §2.1, §2.2
Fase do roadmap: Fase 3
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.audit import service
from app.modules.audit.schemas import AuditoriaOut

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


@router.get("", response_model=list[AuditoriaOut])
def listar_auditoria(
    entidade: str | None = None,
    tipo_evento: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_tenant_session),
) -> list[AuditoriaOut]:
    return service.listar(db, entidade=entidade, tipo_evento=tipo_evento, limit=limit)
