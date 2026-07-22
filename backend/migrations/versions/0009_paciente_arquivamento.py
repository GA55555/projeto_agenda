"""Metadados e invariantes do arquivamento de pacientes (Fase 7i).

O arquivamento preserva prontuario/documentos e tira o paciente das listas
ativas. A FK composta garante no MOTOR que o ator pertence ao mesmo tenant
(§2.1); o CHECK impede estado arquivado sem data. Arquivamento e criacao de
agenda serializam pela linha do paciente, impedindo corrida entre os fluxos.

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_usuarios_tenant_id_id", "usuarios", ["tenant_id", "id"])
    op.add_column(
        "pacientes", sa.Column("arquivado_em", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "pacientes",
        sa.Column("arquivado_por_usuario_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "pacientes", sa.Column("motivo_arquivamento", sa.String(length=500), nullable=True)
    )
    # Compatibilidade com pacientes arquivados antes da Fase 7i.
    op.execute(
        "UPDATE pacientes SET arquivado_em = COALESCE(atualizado_em, now()) WHERE NOT ativo"
    )
    op.create_foreign_key(
        "fk_pacientes_arquivado_por_usuario",
        "pacientes",
        "usuarios",
        ["tenant_id", "arquivado_por_usuario_id"],
        ["tenant_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "paciente_arquivamento_coerente",
        "pacientes",
        "(ativo AND arquivado_em IS NULL AND arquivado_por_usuario_id IS NULL "
        "AND motivo_arquivamento IS NULL) OR (NOT ativo AND arquivado_em IS NOT NULL)",
    )
    op.create_index(
        "ix_pacientes_tenant_id_ativo_nome", "pacientes", ["tenant_id", "ativo", "nome"]
    )


def downgrade() -> None:
    op.drop_index("ix_pacientes_tenant_id_ativo_nome", table_name="pacientes")
    op.drop_constraint("paciente_arquivamento_coerente", "pacientes", type_="check")
    op.drop_constraint("fk_pacientes_arquivado_por_usuario", "pacientes", type_="foreignkey")
    op.drop_column("pacientes", "motivo_arquivamento")
    op.drop_column("pacientes", "arquivado_por_usuario_id")
    op.drop_column("pacientes", "arquivado_em")
    op.drop_constraint("uq_usuarios_tenant_id_id", "usuarios", type_="unique")
