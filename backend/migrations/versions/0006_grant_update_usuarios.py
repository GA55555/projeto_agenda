"""Grant de UPDATE (colunas de perfil) em usuarios ao role de app.

A Fase 7c introduz edicao do proprio perfil (PATCH /auth/me) e troca de senha
(POST /auth/me/senha) — o backend (agenda_app) passa a fazer UPDATE em
`usuarios`, que ate aqui so tinha GRANT SELECT (migration 0002).

Grant EM NIVEL DE COLUNA (§2.1.1, menor privilegio): o role de app so pode
alterar nome/email/senha_hash/atualizado_em do proprio fluxo de perfil. Colunas
administrativas (tenant_id, papel, ativo) continuam fora do alcance do runtime
— alteradas so pelo role admin (CLI/psql break-glass).

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-20
"""
import os
from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = os.environ.get("APP_DB_USER", "agenda_app")
assert APP_ROLE.isidentifier(), f"APP_DB_USER invalido como identificador: {APP_ROLE!r}"


def upgrade() -> None:
    op.execute(
        f'GRANT UPDATE (nome, email, senha_hash, atualizado_em) '
        f'ON TABLE usuarios TO "{APP_ROLE}"'
    )


def downgrade() -> None:
    op.execute(f'REVOKE UPDATE ON TABLE usuarios FROM "{APP_ROLE}"')
