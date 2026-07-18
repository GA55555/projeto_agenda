"""Endpoint de healthcheck (liveness).

Bootstrap da Fase 0. Readiness (checar a BD) entra na Fase 2, quando
existir a sessao/pool. Ver §1.3.

Fase do roadmap: Fase 0 (bootstrap) -> Fase 2
"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: responde 200 se o processo esta de pe."""
    return {"status": "ok"}
