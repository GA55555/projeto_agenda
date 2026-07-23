"""Documentos clinicos privados do paciente (Fase 7k).

O PostgreSQL guarda somente metadados auditaveis. O binario sanitizado fica no
volume privado do backend, referenciado por chave opaca. RLS/FORCE e FKs
compostas garantem isolamento no motor; o role da app nao recebe DELETE para
preservar o prontuario (§0.3/§2.1).

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-22
"""
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from app.db.rls import tenant_rls_statements

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = os.environ.get("APP_DB_USER", "agenda_app")
assert APP_ROLE.isidentifier(), f"APP_DB_USER invalido como identificador: {APP_ROLE!r}"


def upgrade() -> None:
    op.create_table(
        "documentos_paciente",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("paciente_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("enviado_por_usuario_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("nome_original", sa.String(length=255), nullable=False),
        sa.Column("chave_armazenamento", sa.String(length=100), nullable=False),
        sa.Column("tipo_mime", sa.String(length=80), nullable=False),
        sa.Column("extensao", sa.String(length=10), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("tamanho_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documentos_paciente"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_documentos_paciente_tenant_id_id"),
        sa.UniqueConstraint(
            "chave_armazenamento", name="uq_documentos_paciente_chave_armazenamento"
        ),
        sa.CheckConstraint("tamanho_bytes > 0", name="documento_tamanho_positivo"),
        sa.CheckConstraint(
            "(extensao = '.pdf' AND tipo_mime = 'application/pdf') OR "
            "(extensao = '.docx' AND tipo_mime = "
            "'application/vnd.openxmlformats-officedocument.wordprocessingml.document') OR "
            "(extensao = '.jpg' AND tipo_mime = 'image/jpeg') OR "
            "(extensao = '.png' AND tipo_mime = 'image/png')",
            name="documento_tipo_coerente",
        ),
        sa.CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="documento_sha256_valido",
        ),
        sa.CheckConstraint(
            "chave_armazenamento ~ '^[0-9a-f]{2}/[0-9a-f]{32}\\.(pdf|docx|jpg|png)$'",
            name="documento_chave_valida",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "paciente_id"],
            ["pacientes.tenant_id", "pacientes.id"],
            ondelete="RESTRICT",
            name="fk_documentos_paciente_paciente",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "enviado_por_usuario_id"],
            ["usuarios.tenant_id", "usuarios.id"],
            ondelete="RESTRICT",
            name="fk_documentos_paciente_enviado_por_usuario",
        ),
    )
    op.create_index(
        "ix_documentos_paciente_tenant_paciente_criado",
        "documentos_paciente",
        ["tenant_id", "paciente_id", "criado_em"],
    )
    for stmt in tenant_rls_statements("documentos_paciente"):
        op.execute(stmt)
    op.execute(f'GRANT SELECT, INSERT ON TABLE documentos_paciente TO "{APP_ROLE}"')


def downgrade() -> None:
    op.execute(f'REVOKE ALL ON TABLE documentos_paciente FROM "{APP_ROLE}"')
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON documentos_paciente")
    op.drop_table("documentos_paciente")
