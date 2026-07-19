"""Dependencias de autenticacao.

`get_current_user` decodifica o JWT (sem ida a BD) e devolve o contexto do
utilizador autenticado, incluindo o `tenant_id` que alimenta o RLS (§2.1).

O token vem do **cookie httpOnly** da SPA (Fase 7, resistente a XSS) OU do
cabecalho `Authorization: Bearer` (ferramentas/testes/clientes programaticos).
O cookie tem prioridade — e o caminho do browser.

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 2 / Fase 7 (cookie)
"""
import uuid
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.security import decode_access_token


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    tenant_id: uuid.UUID
    papel: str


def _extrair_token(request: Request) -> str | None:
    """Token do cookie httpOnly (SPA) ou do header Authorization (bearer)."""
    cookie = request.cookies.get(settings.cookie_name)
    if cookie:
        return cookie
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer ") :]
    return None


def get_current_user(request: Request) -> CurrentUser:
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nao autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = _extrair_token(request)
    if token is None:
        raise credenciais_invalidas
    try:
        payload = decode_access_token(token)
        return CurrentUser(
            id=uuid.UUID(payload["sub"]),
            tenant_id=uuid.UUID(payload["tenant_id"]),
            papel=payload["papel"],
        )
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credenciais_invalidas
