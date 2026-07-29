"""Transactional outbox do webhook n8n (Fase 8b, §2.1/§4.2).

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-28
"""
import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from app.db.rls import tenant_rls_statements

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = os.environ.get("APP_DB_USER", "agenda_app")
assert APP_ROLE.isidentifier()


def upgrade() -> None:
    op.create_table(
        "n8n_outbox",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("evolucao_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("estado", sa.String(20), server_default="pendente", nullable=False),
        sa.Column("tentativas", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ultima_tentativa_em", sa.DateTime(timezone=True)),
        sa.Column("enviado_em", sa.DateTime(timezone=True)),
        sa.Column("ultimo_erro", sa.String(80)),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_n8n_outbox"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_n8n_outbox_tenant_id_id"),
        sa.UniqueConstraint("tenant_id", "evolucao_id", name="uq_n8n_outbox_evolucao"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "evolucao_id"], ["evolucoes.tenant_id", "evolucoes.id"],
            ondelete="RESTRICT", name="fk_n8n_outbox_evolucao",
        ),
        sa.CheckConstraint("estado IN ('pendente','enviado')", name="n8n_outbox_estado"),
        sa.CheckConstraint("tentativas >= 0", name="n8n_outbox_tentativas"),
    )
    op.create_index("ix_n8n_outbox_tenant_estado_criado", "n8n_outbox", ["tenant_id", "estado", "criado_em"])
    for stmt in tenant_rls_statements("n8n_outbox"):
        op.execute(stmt)
    op.execute(f'GRANT SELECT, INSERT, UPDATE ON TABLE n8n_outbox TO "{APP_ROLE}"')


def downgrade() -> None:
    op.execute(f'REVOKE ALL ON TABLE n8n_outbox FROM "{APP_ROLE}"')
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON n8n_outbox")
    op.drop_table("n8n_outbox")
