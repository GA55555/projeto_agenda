"""Router raiz da API v1: agrega os routers de cada modulo de dominio sob /api/v1.

Fase do roadmap: Fase 2
"""
from fastapi import APIRouter

from app.modules.agendamentos.router import router as agendamentos_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.consentimentos.router import router as consentimentos_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.documentos.router import router as documentos_router
from app.modules.evolucoes.router import router as evolucoes_router
from app.modules.llm.router import router as llm_router
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
# Fase 3.5 — agenda de atendimentos
api_router.include_router(agendamentos_router)
# Fase 5 — evolucoes clinicas + RAG (embeddings)
api_router.include_router(evolucoes_router)
# Fase 6 — geracao de evolucoes via LLM (tunel opaco)
api_router.include_router(llm_router)
# Fase 7c — resumo/visao geral (dashboard)
api_router.include_router(dashboard_router)
# Fase 7k — documentos clinicos privados e sanitizados
api_router.include_router(documentos_router)
