"""Schemas Pydantic do modulo de autenticacao.

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 2
"""
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    nome: str
    papel: str
    tenant_id: uuid.UUID


class PerfilOut(BaseModel):
    """Contexto do utilizador logado para o menu de perfil da SPA (Fase 7c)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    papel: str
    nome: str
    email: EmailStr
