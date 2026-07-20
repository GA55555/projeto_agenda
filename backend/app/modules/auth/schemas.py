"""Schemas Pydantic do modulo de autenticacao.

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 2
"""
import uuid

from pydantic import BaseModel, ConfigDict


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # Response model: serializa e-mail JA gravado (confiavel) -> `str`, nao
    # `EmailStr`. Revalidar na saida quebra e-mails validos-mas-reservados
    # (ex.: `.local`), que o email-validator rejeita. EmailStr fica so na entrada.
    email: str
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
    email: str  # str, nao EmailStr (ver UsuarioOut) — nao revalidar na saida
