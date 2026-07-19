"""Modelo do agendamento (agenda de atendimentos) — Fase 3.5.

Tabela clinica: `tenant_id` + RLS/FORCE (na migration). O paciente e referenciado
por CHAVE COMPOSTA `(tenant_id, paciente_id)` — a BD garante que o paciente e do
mesmo tenant (§2.1), sem depender da aplicacao.

Regra de negocio NO MOTOR (§2.1): nao ha dois atendimentos nao-cancelados do
mesmo tenant com horarios sobrepostos. Imposto por uma constraint EXCLUDE
(GiST sobre `tstzrange(inicio, fim)` + `tenant_id`), definida na migration
(EXCLUDE nao se expressa de forma limpa no ORM; a BD e a fonte da verdade).

Cancelamento e SOFT (status='cancelado' + `motivo_cancelamento`); nunca DELETE.

Regras de ouro: §2.1, §3.2
Fase do roadmap: Fase 3.5
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Vocabulario controlado do status (CHECK na migration).
STATUS_AGENDADO = "agendado"
STATUS_REALIZADO = "realizado"
STATUS_CANCELADO = "cancelado"
STATUS_FALTA = "falta"
STATUS_AGENDAMENTO = (STATUS_AGENDADO, STATUS_REALIZADO, STATUS_CANCELADO, STATUS_FALTA)


class Agendamento(Base):
    __tablename__ = "agendamentos"
    __table_args__ = (
        # FK composto: paciente do MESMO tenant do agendamento (§2.1).
        ForeignKeyConstraint(
            ["tenant_id", "paciente_id"],
            ["pacientes.tenant_id", "pacientes.id"],
            ondelete="RESTRICT",
            name="fk_agendamentos_paciente",
        ),
        CheckConstraint("fim > inicio", name="fim_apos_inicio"),
        CheckConstraint(
            "status IN ('agendado','realizado','cancelado','falta')",
            name="status_valido",
        ),
        # Listagem por data (agenda) e por paciente (§3.2).
        Index("ix_agendamentos_tenant_id_inicio", "tenant_id", "inicio"),
        Index("ix_agendamentos_paciente_id", "paciente_id"),
        # A constraint EXCLUDE anti-sobreposicao vive na migration (§2.1).
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fim: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'agendado'")
    )
    tipo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    observacao: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    motivo_cancelamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )
