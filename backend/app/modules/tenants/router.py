"""Rotas do modulo de tenants.

`GET /tenants/atual` roda sob `get_tenant_session` (RLS ativo): um `SELECT`
generico em `tenants` so devolve a linha do locatario do JWT — prova, pela API,
que o isolamento funciona ponta a ponta (§2.1).

Regras de ouro: §2.1
Fase do roadmap: Fase 2
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.tenants.models import Tenant
from app.modules.tenants.schemas import TenantOut

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/atual", response_model=TenantOut)
def tenant_atual(db: Session = Depends(get_tenant_session)) -> Tenant:
    # SELECT generico: o RLS restringe ao locatario ativo (contexto do JWT).
    tenant = db.execute(select(Tenant)).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant nao encontrado")
    return tenant
