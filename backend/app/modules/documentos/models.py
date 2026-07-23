"""Metadados de documentos clinicos; o binario fica no volume privado.

Toda linha tem tenant_id e FKs compostas para paciente e autor do upload. RLS
e retencao sem DELETE sao impostas na migration 0010 (§0.3/§2.1).
"""
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKeyConstraint, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentoPaciente(Base):
    __tablename__ = "documentos_paciente"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_documentos_paciente_tenant_id_id"),
        UniqueConstraint("chave_armazenamento", name="uq_documentos_paciente_chave_armazenamento"),
        ForeignKeyConstraint(
            ["tenant_id", "paciente_id"],
            ["pacientes.tenant_id", "pacientes.id"],
            ondelete="RESTRICT",
            name="fk_documentos_paciente_paciente",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "enviado_por_usuario_id"],
            ["usuarios.tenant_id", "usuarios.id"],
            ondelete="RESTRICT",
            name="fk_documentos_paciente_enviado_por_usuario",
        ),
        CheckConstraint("tamanho_bytes > 0", name="documento_tamanho_positivo"),
        CheckConstraint(
            "(extensao = '.pdf' AND tipo_mime = 'application/pdf') OR "
            "(extensao = '.docx' AND tipo_mime = "
            "'application/vnd.openxmlformats-officedocument.wordprocessingml.document') OR "
            "(extensao = '.jpg' AND tipo_mime = 'image/jpeg') OR "
            "(extensao = '.png' AND tipo_mime = 'image/png')",
            name="documento_tipo_coerente",
        ),
        CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'", name="documento_sha256_valido"
        ),
        CheckConstraint(
            "chave_armazenamento ~ '^[0-9a-f]{2}/[0-9a-f]{32}\\.(pdf|docx|jpg|png)$'",
            name="documento_chave_valida",
        ),
        Index(
            "ix_documentos_paciente_tenant_paciente_criado",
            "tenant_id",
            "paciente_id",
            "criado_em",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    enviado_por_usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    chave_armazenamento: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo_mime: Mapped[str] = mapped_column(String(80), nullable=False)
    extensao: Mapped[str] = mapped_column(String(10), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
