"""tenancy foundation: tabela tenants + RLS (FORCE) + grants ao role de app

Cria a raiz do multitenancy e prova o mecanismo de RLS (§2.1/§2.1.1).
O role `agenda_app` (NOSUPERUSER) e provisionado no init do cluster
(infra/postgres/init/02-roles.sh); aqui apenas concedemos privilegios a ele.

Sem indice vetorial (§3.1). Indices B-Tree de pre-filtragem (§3.2) entram
junto das tabelas clinicas na Fase 3.

Revision ID: 0001
Revises:
Create Date: 2026-07-17
"""
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from app.db.rls import tenant_rls_statements

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Role de aplicacao (do ambiente). Validado como identificador simples para uso
# seguro como identificador SQL (nao ha bind de identificadores em DDL).
APP_ROLE = os.environ.get("APP_DB_USER", "agenda_app")
assert APP_ROLE.isidentifier(), f"APP_DB_USER invalido como identificador: {APP_ROLE!r}"


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column(
            "id", pg.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_tenants"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )

    # RLS na propria tenants: um locatario so enxerga a SUA linha (chave = id).
    for stmt in tenant_rls_statements("tenants", tenant_column="id"):
        op.execute(stmt)

    # O role de app pode ler tenants (a visibilidade por linha e imposta pelo RLS).
    # Provisionamento de tenants e tarefa administrativa (agenda_admin).
    op.execute(f'GRANT SELECT ON TABLE tenants TO "{APP_ROLE}"')


def downgrade() -> None:
    op.execute(f'REVOKE ALL ON TABLE tenants FROM "{APP_ROLE}"')
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON tenants")
    op.drop_table("tenants")
