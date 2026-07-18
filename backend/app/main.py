"""Ponto de entrada da aplicacao FastAPI.

Bootstrap minimo da Fase 0 (montagem do app + GC + healthcheck).
A Fase 2 expande: middleware de tenant (SET LOCAL), routers dos modulos,
autenticacao. Ver §1.3 (GC, workers) e §2.1.

Regras de ouro: §1.3
Fase do roadmap: Fase 0 (bootstrap) -> Fase 2
"""
import gc

from fastapi import FastAPI

# Servico de longa duracao: varreduras mais frequentes mantem a RAM linear (§1.3).
gc.set_threshold(700, 10, 10)

app = FastAPI(
    title="Agenda de Atendimentos API",
    version="0.1.0",
)

from app.api.health import router as health_router  # noqa: E402
from app.api.router import api_router  # noqa: E402

app.include_router(health_router)
app.include_router(api_router)
