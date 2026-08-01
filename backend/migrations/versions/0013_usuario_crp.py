"""Registro profissional CRP no perfil da psicologa.

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-31
"""
import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = os.environ.get("APP_DB_USER", "agenda_app")
assert APP_ROLE.isidentifier()


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("crp", sa.String(10), nullable=True))
    op.create_check_constraint(
        "usuario_crp_formato",
        "usuarios",
        "crp IS NULL OR crp ~ '^[0-9]{2}/[0-9]{4,7}$'",
    )
    op.execute(f'GRANT UPDATE (crp) ON TABLE usuarios TO "{APP_ROLE}"')


def downgrade() -> None:
    op.execute(f'REVOKE UPDATE (crp) ON TABLE usuarios FROM "{APP_ROLE}"')
    op.drop_constraint("usuario_crp_formato", "usuarios", type_="check")
    op.drop_column("usuarios", "crp")
