"""Modelos de evolucoes clinicas + chunks vetorizados (§3.1/§3.2/§3.4).

`evolucoes` guarda a nota clinica CRUA e legivel (sistema de registro da
psicologa), sob RLS+FORCE (§2.1). `evolucao_chunks` guarda os blocos da nota
(§3.3) + o `embedding` (pgvector, 1536 dims).

§3.4 (superficie IA↔BD): o `texto_chunk` fica CRU (a psicologa le), mas o
embedding deriva SOMENTE do texto anonimizado (calculado no service) — o vetor
nunca e um deposito de PII recuperavel. `paciente_id` e denormalizado no chunk
porque a filtragem hibrida (§3.2) precisa dele NA tabela vetorial, antes do `<=>`.

Isolamento no MOTOR (§2.1): FK composto `(tenant_id, ...)` garante que evolucao
e chunk pertencem ao mesmo tenant do paciente/evolucao — sem checagem na app.

Regras de ouro: §2.1, §3.1, §3.2, §3.4
Fase do roadmap: Fase 5
"""
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKeyConstraint, Integer, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

EMBEDDING_DIMS = 1536  # text-embedding-3-small (§3.1)


class Evolucao(Base):
    __tablename__ = "evolucoes"
    # Alvo do FK composto (tenant_id, id) vindo dos chunks (§2.1).
    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_evolucoes_tenant_id_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    autor_usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # Nota clinica CRUA e legivel (sob RLS). Nunca sai assim para o LLM (§3.4).
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    chunks: Mapped[list["EvolucaoChunk"]] = relationship(
        back_populates="evolucao",
        primaryjoin="Evolucao.id == EvolucaoChunk.evolucao_id",
        foreign_keys="[EvolucaoChunk.evolucao_id]",
        viewonly=True,
    )


class EvolucaoChunk(Base):
    __tablename__ = "evolucao_chunks"
    __table_args__ = (
        # FK composto: chunk e evolucao sao do MESMO tenant (§2.1).
        ForeignKeyConstraint(
            ["tenant_id", "evolucao_id"],
            ["evolucoes.tenant_id", "evolucoes.id"],
            ondelete="CASCADE",
            name="fk_evolucao_chunks_evolucao",
        ),
        UniqueConstraint(
            "tenant_id", "evolucao_id", "ordem",
            name="uq_evolucao_chunks_tenant_id_evolucao_id_ordem",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # Denormalizado do paciente da evolucao -> pre-filtro hibrido §3.2.
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    evolucao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    texto_chunk: Mapped[str] = mapped_column(Text, nullable=False)  # CRU (sob RLS)
    # Nullable: se a OpenAI falhar, a nota persiste com embedding PENDENTE e um
    # re-embed posterior resolve (decisao Fase 5). Sem indice vetorial (§3.1).
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMS), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    evolucao: Mapped["Evolucao"] = relationship(
        back_populates="chunks",
        primaryjoin="EvolucaoChunk.evolucao_id == Evolucao.id",
        foreign_keys=[evolucao_id],
        viewonly=True,
    )
