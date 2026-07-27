"""Assinatura eletrônica e imutabilidade das evoluções clínicas.

O clique explícito "Assinar e gravar", feito por usuário autenticado, passa a
ser registrado na própria evolução e na auditoria append-only. O conteúdo
assinado não pode sofrer UPDATE/DELETE, mesmo pelo dono da tabela, sem uma ação
administrativa deliberada sobre o trigger (§2.2/§4.2).

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-27
"""
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = os.environ.get("APP_DB_USER", "agenda_app")
assert APP_ROLE.isidentifier(), f"APP_DB_USER invalido como identificador: {APP_ROLE!r}"


def upgrade() -> None:
    op.add_column(
        "evolucoes",
        sa.Column("assinada_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "evolucoes",
        sa.Column("assinada_por_usuario_id", pg.UUID(as_uuid=True), nullable=True),
    )
    # Evoluções anteriores já nasceram pelo fluxo autenticado "aprovar e gravar".
    # O backfill preserva seu autor e instante originais, sem inventar nova data.
    op.execute(
        "UPDATE evolucoes "
        "SET assinada_em = criado_em, assinada_por_usuario_id = autor_usuario_id "
        "WHERE assinada_em IS NULL"
    )
    op.alter_column("evolucoes", "assinada_em", nullable=False)
    op.alter_column("evolucoes", "assinada_por_usuario_id", nullable=False)
    op.create_foreign_key(
        "fk_evolucoes_assinada_por_usuario",
        "evolucoes",
        "usuarios",
        ["tenant_id", "assinada_por_usuario_id"],
        ["tenant_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "assinante_autor",
        "evolucoes",
        "assinada_por_usuario_id = autor_usuario_id",
    )

    # A nota assinada é append-only. Embeddings pendentes continuam atualizáveis
    # em evolucao_chunks; não há motivo legítimo para alterar a nota original.
    op.execute(f'REVOKE UPDATE ON TABLE evolucoes FROM "{APP_ROLE}"')
    op.execute(
        """
        CREATE OR REPLACE FUNCTION impedir_mutacao_evolucao_assinada()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'evolucao assinada e imutavel: UPDATE/DELETE proibido (§2.2/§4.2)';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_evolucao_assinada_imutavel
            BEFORE UPDATE OR DELETE ON evolucoes
            FOR EACH ROW EXECUTE FUNCTION impedir_mutacao_evolucao_assinada();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_evolucao_assinada_imutavel ON evolucoes")
    op.execute("DROP FUNCTION IF EXISTS impedir_mutacao_evolucao_assinada()")
    op.execute(f'GRANT UPDATE ON TABLE evolucoes TO "{APP_ROLE}"')
    op.drop_constraint("assinante_autor", "evolucoes", type_="check")
    op.drop_constraint("fk_evolucoes_assinada_por_usuario", "evolucoes", type_="foreignkey")
    op.drop_column("evolucoes", "assinada_por_usuario_id")
    op.drop_column("evolucoes", "assinada_em")
