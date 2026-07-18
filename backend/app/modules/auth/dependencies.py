"""Dependencias de autenticacao.

`get_current_user` decodifica o JWT (sem ida a BD) e devolve o contexto do
utilizador autenticado, incluindo o `tenant_id` que alimenta o RLS (§2.1).

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 2
"""
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    tenant_id: uuid.UUID
    papel: str


def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nao autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        return CurrentUser(
            id=uuid.UUID(payload["sub"]),
            tenant_id=uuid.UUID(payload["tenant_id"]),
            papel=payload["papel"],
        )
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credenciais_invalidas
