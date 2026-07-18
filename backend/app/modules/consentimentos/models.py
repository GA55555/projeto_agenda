"""Modelo do consentimento (TCLE) — §2.2.

Tabela clinica: `tenant_id` + RLS/FORCE (na migration). O TCLE NAO tem clausulas
genericas: `finalidade_clinica` e `limitacoes_acesso` sao especificos e
obrigatorios (§2.2). Guarda tambem o texto/versao do termo apresentado.

A geracao do PDF do termo e tarefa do n8n (Fase 8); aqui persistimos os
metadados e o texto do consentimento concedido.

Revogacao = setar `revogado_em`/`revogado_por_usuario_id` (UPDATE). O registro
INDELEVEL da revogacao vai para `auditoria` (append-only, §2.2).

Regras de ouro: §2.1, §2.2
Fase do roadmap: Fase 3
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Consentimento(Base):
    __tablename__ = "consentimentos"
    __table_args__ = (
        # FK compostos: paciente e responsavel do MESMO tenant do consentimento (§2.1).
        ForeignKeyConstraint(
            ["tenant_id", "paciente_id"],
            ["pacientes.tenant_id", "pacientes.id"],
            ondelete="RESTRICT",
            name="fk_consentimentos_paciente",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "responsavel_id"],
            ["responsaveis_legais.tenant_id", "responsaveis_legais.id"],
            ondelete="RESTRICT",
            name="fk_consentimentos_responsavel",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    responsavel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    finalidade_clinica: Mapped[str] = mapped_column(Text, nullable=False)
    limitacoes_acesso: Mapped[str] = mapped_column(Text, nullable=False)
    termo_versao: Mapped[str] = mapped_column(String(50), nullable=False)
    termo_texto: Mapped[str] = mapped_column(Text, nullable=False)
    concedido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    concedido_por_usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revogado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
