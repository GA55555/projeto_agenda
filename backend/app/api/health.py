"""Endpoints de healthcheck.

- `/health`        liveness: o processo esta de pe.
- `/health/ready`  readiness: a BD responde (SELECT 1 como agenda_app).

Regras de ouro: §1.3
Fase do roadmap: Fase 0 (liveness) -> Fase 2 (readiness)
"""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.db.session import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: responde 200 se o processo esta de pe."""
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> dict[str, str]:
    """Readiness: confirma que a BD responde."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="BD indisponivel"
        )
    return {"status": "ready"}
