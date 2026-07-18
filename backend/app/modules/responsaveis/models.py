"""Modelo do responsavel legal (§2.2).

Tabela clinica: `tenant_id` + RLS/FORCE (aplicados na migration via helper
`tenant_rls_statements`). O CPF e PII e vive dentro da fronteira do RLS —
unico POR tenant (nunca cross-tenant).

O vinculo com o(s) paciente(s) e N:N e mora em `pacientes.models` (tabela
`vinculos_resp_paciente`): um responsavel pode ter varios pacientes (irmaos)
e um paciente varios responsaveis (pai/mae, guarda compartilhada).

Regras de ouro: §2.1, §2.2
Fase do roadmap: Fase 3
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ResponsavelLegal(Base):
    __tablename__ = "responsaveis_legais"
    # Alvo do FK composto (tenant_id, id) vindo dos vinculos/consentimentos (§2.1).
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_responsaveis_legais_tenant_id_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    cpf: Mapped[str] = mapped_column(String(14), nullable=False)  # PII (dentro do RLS)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    endereco: Mapped[str | None] = mapped_column(String(300), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
