"""Router raiz da API v1: agrega os routers de cada modulo de dominio sob /api/v1.

Fase do roadmap: Fase 2
"""
from fastapi import APIRouter

from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.consentimentos.router import router as consentimentos_router
from app.modules.pacientes.router import router as pacientes_router
from app.modules.responsaveis.router import router as responsaveis_router
from app.modules.tenants.router import router as tenants_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(tenants_router)
# Fase 3 — dominio & consentimento
api_router.include_router(responsaveis_router)
api_router.include_router(pacientes_router)
api_router.include_router(consentimentos_router)
api_router.include_router(audit_router)
