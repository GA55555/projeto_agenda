"""Dependencias de autenticacao.

`get_current_user` decodifica o JWT e confirma no control-plane que a conta
continua ativa antes de devolver o contexto que alimenta o RLS (§2.1). Essa
consulta curta torna a suspensão efetiva inclusive para JWTs já emitidos.

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
from sqlalchemy import select

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import SessionLocal


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


def _decodificar_current_user(request: Request) -> CurrentUser:
    """Valida o JWT e devolve suas claims tipadas, sem consultar o banco."""
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


def _conta_continua_ativa(user: CurrentUser) -> bool:
    """Confirma identidade/tenant/papel atuais; falha fechada para conta suspensa."""
    # Import local evita acoplamento de import entre dependencias e o modelo de auth.
    from app.modules.auth.models import Usuario

    with SessionLocal() as db:
        usuario_id = db.execute(
            select(Usuario.id).where(
                Usuario.id == user.id,
                Usuario.tenant_id == user.tenant_id,
                Usuario.papel == user.papel,
                Usuario.ativo.is_(True),
            )
        ).scalar_one_or_none()
    return usuario_id is not None


def get_current_user(request: Request) -> CurrentUser:
    """Autentica o token e revoga imediatamente sessões de contas desativadas."""
    user = _decodificar_current_user(request)
    if not _conta_continua_ativa(user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nao autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
