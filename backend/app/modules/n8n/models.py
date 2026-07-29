"""Transactional outbox do n8n, isolado por RLS (§2.1/§4.2)."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class N8nOutbox(Base):
    __tablename__ = "n8n_outbox"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_n8n_outbox_tenant_id_id"),
        UniqueConstraint("tenant_id", "evolucao_id", name="uq_n8n_outbox_evolucao"),
        ForeignKeyConstraint(
            ["tenant_id", "evolucao_id"],
            ["evolucoes.tenant_id", "evolucoes.id"],
            ondelete="RESTRICT",
            name="fk_n8n_outbox_evolucao",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    evolucao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pendente")
    tentativas: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    ultima_tentativa_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enviado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_erro: Mapped[str | None] = mapped_column(String(80))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
