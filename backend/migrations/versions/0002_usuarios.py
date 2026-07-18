"""usuarios: tabela de identidade/login (control-plane) + grant ao role de app

Sem RLS por tenant (email global unico) para o login descobrir o tenant antes
de autenticar — exceção deliberada; tabelas clinicas mantem RLS+FORCE (§2.1.1).
O role de app recebe apenas SELECT (login por email); criacao de usuarios e
tarefa administrativa (CLI com role admin).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-18
"""
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = os.environ.get("APP_DB_USER", "agenda_app")
assert APP_ROLE.isidentifier(), f"APP_DB_USER invalido como identificador: {APP_ROLE!r}"


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("senha_hash", sa.String(length=255), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("papel", sa.String(length=20), server_default=sa.text("'psicologa'"), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_usuarios"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_usuarios_tenant_id_tenants", ondelete="RESTRICT"),
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
    )
    # Indice para o lookup de login e para juntar por tenant.
    op.create_index("ix_usuarios_tenant_id", "usuarios", ["tenant_id"])

    # Sem RLS (control-plane). App so precisa ler para autenticar.
    op.execute(f'GRANT SELECT ON TABLE usuarios TO "{APP_ROLE}"')


def downgrade() -> None:
    op.execute(f'REVOKE ALL ON TABLE usuarios FROM "{APP_ROLE}"')
    op.drop_index("ix_usuarios_tenant_id", table_name="usuarios")
    op.drop_table("usuarios")
