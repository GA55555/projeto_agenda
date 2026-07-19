"""agendamentos: agenda de atendimentos (Fase 3.5)

Tabela clinica com `tenant_id` + RLS ENABLE/FORCE + politica `tenant_isolation`
(§2.1/§2.1.1). Paciente por FK composto `(tenant_id, paciente_id)` (link
intra-tenant garantido pela BD, §2.1). Indices B-Tree de listagem (§3.2).

Regra de negocio NO MOTOR (§2.1): sem sobreposicao de horarios do mesmo tenant.
Imposta por EXCLUDE (GiST) sobre `tstzrange(inicio, fim)`, ignorando cancelados.
Requer a extensao `btree_gist` (para comparar `tenant_id` com `=` no indice GiST).

Cancelamento e SOFT (grants sem DELETE — retencao clinica).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-19
"""
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from app.db.rls import tenant_rls_statements

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = os.environ.get("APP_DB_USER", "agenda_app")
assert APP_ROLE.isidentifier(), f"APP_DB_USER invalido como identificador: {APP_ROLE!r}"


def upgrade() -> None:
    # btree_gist permite usar `tenant_id WITH =` num indice GiST (junto do range).
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "agendamentos",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("paciente_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'agendado'"), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=True),
        sa.Column("observacao", sa.String(length=1000), nullable=True),
        sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_agendamentos"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "paciente_id"],
            ["pacientes.tenant_id", "pacientes.id"],
            name="fk_agendamentos_paciente",
            ondelete="RESTRICT",
        ),
        # Convencao ck_%(table_name)s_%(constraint_name)s -> passar so o sufixo.
        sa.CheckConstraint("fim > inicio", name="fim_apos_inicio"),
        sa.CheckConstraint(
            "status IN ('agendado','realizado','cancelado','falta')",
            name="status_valido",
        ),
    )
    op.create_index("ix_agendamentos_tenant_id_inicio", "agendamentos", ["tenant_id", "inicio"])
    op.create_index("ix_agendamentos_paciente_id", "agendamentos", ["paciente_id"])

    # Anti-sobreposicao NO MOTOR (§2.1): mesmo tenant, ranges que se tocam, exceto
    # cancelados. `&&` = ranges se sobrepoem; `tstzrange(inicio, fim, '[)')` = fim
    # exclusivo, entao um atendimento que comeca exatamente quando outro termina
    # NAO colide.
    op.execute(
        "ALTER TABLE agendamentos ADD CONSTRAINT ex_agendamentos_sem_sobreposicao "
        "EXCLUDE USING gist ("
        "  tenant_id WITH =, "
        "  tstzrange(inicio, fim, '[)') WITH &&"
        ") WHERE (status <> 'cancelado')"
    )

    # RLS (FORCE) + politica de isolamento (§2.1/§2.1.1).
    for stmt in tenant_rls_statements("agendamentos"):
        op.execute(stmt)

    # Grants: leitura/escrita, sem DELETE (cancelamento e soft).
    op.execute(f'GRANT SELECT, INSERT, UPDATE ON TABLE agendamentos TO "{APP_ROLE}"')


def downgrade() -> None:
    op.execute(f'REVOKE ALL ON TABLE agendamentos FROM "{APP_ROLE}"')
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON agendamentos")
    op.drop_table("agendamentos")
    # A extensao btree_gist e deixada instalada (pode ser usada por outras tabelas).
