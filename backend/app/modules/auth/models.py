"""Modelo de identidade/login (`usuarios`).

Tabela de *control-plane*: email GLOBALMENTE unico, SEM RLS por tenant — para
o login descobrir o tenant antes de autenticar. Nao guarda dados clinicos;
as tabelas clinicas (Fase 3) sim tem RLS + FORCE (§2.1/§2.1.1).

Cada usuario pertence a um tenant (psicologa). O `tenant_id` do JWT define o
contexto de RLS das requisicoes autenticadas.

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 2
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    papel: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'psicologa'"))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
