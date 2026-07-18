"""Router raiz da API v1: agrega os routers de cada modulo de dominio sob /api/v1.

Fase do roadmap: Fase 2
"""
from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.tenants.router import router as tenants_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(tenants_router)
