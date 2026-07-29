"""Despacho autenticado do outbox n8n; nunca recebe payload clínico do cliente."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.n8n import service

router = APIRouter(prefix="/integracoes/n8n", tags=["integracoes"])


@router.post("/pendentes/despachar")
def despachar_pendentes(
    db: Annotated[Session, Depends(get_tenant_session)],
) -> dict[str, int]:
    enviados, pendentes = service.despachar_pendentes(db)
    return {"enviados": enviados, "pendentes": pendentes}


@router.post("/eventos/{evento_id}/despachar")
def despachar_evento(
    evento_id: uuid.UUID,
    db: Annotated[Session, Depends(get_tenant_session)],
) -> dict[str, bool]:
    if not service.despachar(db, evento_id):
        raise HTTPException(status_code=503, detail="Evento pendente; n8n indisponivel")
    return {"entregue": True}
