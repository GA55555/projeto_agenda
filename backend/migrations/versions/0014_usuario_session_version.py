"""Versao de sessao para revogacao imediata de JWTs.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-02
"""
import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = os.environ.get("APP_DB_USER", "agenda_app")
assert APP_ROLE.isidentifier()


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("session_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.create_check_constraint(
        "usuario_session_version_positiva",
        "usuarios",
        "session_version >= 1",
    )
    op.execute(f'GRANT UPDATE (session_version) ON TABLE usuarios TO "{APP_ROLE}"')


def downgrade() -> None:
    op.execute(f'REVOKE UPDATE (session_version) ON TABLE usuarios FROM "{APP_ROLE}"')
    op.drop_constraint("usuario_session_version_positiva", "usuarios", type_="check")
    op.drop_column("usuarios", "session_version")
