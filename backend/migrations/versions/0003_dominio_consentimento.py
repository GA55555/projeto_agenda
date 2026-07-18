"""dominio & consentimento: responsaveis, pacientes, vinculos N:N, TCLE e auditoria

Fase 3 (§2.2). Todas as tabelas sao clinicas: `tenant_id` + RLS ENABLE/FORCE +
politica `tenant_isolation` (fail-closed) via helper `tenant_rls_statements`
(§2.1/§2.1.1). Indices B-Tree de pre-filtragem por `tenant_id`/`paciente_id`
(§3.2). Nenhum indice vetorial (§3.1).

Auditoria imutavel (append-only, §2.2): o role de app recebe apenas INSERT/SELECT
(sem UPDATE/DELETE) e um trigger BEFORE UPDATE OR DELETE levanta excecao — barra
ate o dono da tabela.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-18
"""
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from app.db.rls import tenant_rls_statements

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = os.environ.get("APP_DB_USER", "agenda_app")
assert APP_ROLE.isidentifier(), f"APP_DB_USER invalido como identificador: {APP_ROLE!r}"

# Tabelas clinicas comuns: RLS + grants de leitura/escrita (sem DELETE — dados
# clinicos nao sao apagados em fluxo normal).
_CLINICAS_RW = ("responsaveis_legais", "pacientes", "vinculos_resp_paciente", "consentimentos")


def _uuid_pk(name: str) -> sa.Column:
    return sa.Column(
        name, pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False
    )


def _ts(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)


def upgrade() -> None:
    # ---- responsaveis_legais ----
    op.create_table(
        "responsaveis_legais",
        _uuid_pk("id"),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("cpf", sa.String(length=14), nullable=False),
        sa.Column("data_nascimento", sa.Date(), nullable=True),
        sa.Column("telefone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("endereco", sa.String(length=300), nullable=True),
        _ts("criado_em"),
        _ts("atualizado_em"),
        sa.PrimaryKeyConstraint("id", name="pk_responsaveis_legais"),
        sa.UniqueConstraint("tenant_id", "cpf", name="uq_responsaveis_legais_tenant_id_cpf"),
        # Alvo do FK composto (tenant_id, id) — garante link intra-tenant (§2.1).
        sa.UniqueConstraint("tenant_id", "id", name="uq_responsaveis_legais_tenant_id_id"),
    )
    op.create_index("ix_responsaveis_legais_tenant_id", "responsaveis_legais", ["tenant_id"])

    # ---- pacientes ----
    op.create_table(
        "pacientes",
        _uuid_pk("id"),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("data_nascimento", sa.Date(), nullable=False),
        sa.Column("sexo", sa.String(length=20), nullable=True),
        sa.Column("observacoes_gerais", sa.String(length=1000), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        _ts("criado_em"),
        _ts("atualizado_em"),
        sa.PrimaryKeyConstraint("id", name="pk_pacientes"),
        # Alvo do FK composto (tenant_id, id) — garante link intra-tenant (§2.1).
        sa.UniqueConstraint("tenant_id", "id", name="uq_pacientes_tenant_id_id"),
    )
    op.create_index("ix_pacientes_tenant_id", "pacientes", ["tenant_id"])

    # ---- vinculos_resp_paciente (N:N) ----
    op.create_table(
        "vinculos_resp_paciente",
        _uuid_pk("id"),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("responsavel_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("paciente_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo_vinculo", sa.String(length=20), nullable=False),
        sa.Column("detem_guarda", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("principal", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        _ts("criado_em"),
        _ts("atualizado_em"),
        sa.PrimaryKeyConstraint("id", name="pk_vinculos_resp_paciente"),
        # FK compostos (tenant_id, *) — a BD garante link intra-tenant (§2.1).
        sa.ForeignKeyConstraint(
            ["tenant_id", "responsavel_id"],
            ["responsaveis_legais.tenant_id", "responsaveis_legais.id"],
            name="fk_vinculos_resp_paciente_responsavel",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "paciente_id"],
            ["pacientes.tenant_id", "pacientes.id"],
            name="fk_vinculos_resp_paciente_paciente",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "tenant_id", "responsavel_id", "paciente_id",
            name="uq_vinculos_resp_paciente_tenant_id_responsavel_id_paciente_id",
        ),
        sa.CheckConstraint(
            "tipo_vinculo IN ('mae','pai','tutor','avo','outro')",
            name="tipo_vinculo",  # convencao ck_%(table_name)s_%(constraint_name)s
        ),
    )
    op.create_index("ix_vinculos_resp_paciente_tenant_id", "vinculos_resp_paciente", ["tenant_id"])
    op.create_index("ix_vinculos_resp_paciente_paciente_id", "vinculos_resp_paciente", ["paciente_id"])
    op.create_index(
        "ix_vinculos_resp_paciente_responsavel_id", "vinculos_resp_paciente", ["responsavel_id"]
    )

    # ---- consentimentos (TCLE) ----
    op.create_table(
        "consentimentos",
        _uuid_pk("id"),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("paciente_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("responsavel_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("finalidade_clinica", sa.Text(), nullable=False),
        sa.Column("limitacoes_acesso", sa.Text(), nullable=False),
        sa.Column("termo_versao", sa.String(length=50), nullable=False),
        sa.Column("termo_texto", sa.Text(), nullable=False),
        _ts("concedido_em"),
        sa.Column("concedido_por_usuario_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("revogado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revogado_por_usuario_id", pg.UUID(as_uuid=True), nullable=True),
        _ts("criado_em"),
        sa.PrimaryKeyConstraint("id", name="pk_consentimentos"),
        # FK compostos (tenant_id, *) — link intra-tenant garantido pela BD (§2.1).
        sa.ForeignKeyConstraint(
            ["tenant_id", "paciente_id"],
            ["pacientes.tenant_id", "pacientes.id"],
            name="fk_consentimentos_paciente", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "responsavel_id"],
            ["responsaveis_legais.tenant_id", "responsaveis_legais.id"],
            name="fk_consentimentos_responsavel", ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_consentimentos_tenant_id", "consentimentos", ["tenant_id"])
    op.create_index("ix_consentimentos_paciente_id", "consentimentos", ["paciente_id"])

    # ---- auditoria (append-only, imutavel) ----
    op.create_table(
        "auditoria",
        _uuid_pk("id"),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo_evento", sa.String(length=60), nullable=False),
        sa.Column("entidade", sa.String(length=60), nullable=False),
        sa.Column("entidade_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("ator_usuario_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", pg.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        _ts("criado_em"),
        sa.PrimaryKeyConstraint("id", name="pk_auditoria"),
    )
    op.create_index("ix_auditoria_tenant_id", "auditoria", ["tenant_id"])
    op.create_index("ix_auditoria_entidade", "auditoria", ["entidade", "entidade_id"])

    # ---- RLS (FORCE) em todas as tabelas clinicas (§2.1/§2.1.1) ----
    for tabela in (*_CLINICAS_RW, "auditoria"):
        for stmt in tenant_rls_statements(tabela):
            op.execute(stmt)

    # ---- Grants ao role de app (§2.1.1) ----
    # Tabelas de dominio: leitura/escrita (sem DELETE — retencao clinica).
    for tabela in _CLINICAS_RW:
        op.execute(f'GRANT SELECT, INSERT, UPDATE ON TABLE {tabela} TO "{APP_ROLE}"')
    # Auditoria: append-only — apenas INSERT/SELECT (sem UPDATE/DELETE).
    op.execute(f'GRANT SELECT, INSERT ON TABLE auditoria TO "{APP_ROLE}"')

    # ---- Imutabilidade da auditoria imposta no motor (§2.2) ----
    op.execute(
        """
        CREATE OR REPLACE FUNCTION impedir_mutacao_auditoria() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'auditoria e append-only: UPDATE/DELETE proibido (§2.2)';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_auditoria_imutavel
            BEFORE UPDATE OR DELETE ON auditoria
            FOR EACH ROW EXECUTE FUNCTION impedir_mutacao_auditoria();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_auditoria_imutavel ON auditoria")
    op.execute("DROP FUNCTION IF EXISTS impedir_mutacao_auditoria()")

    for tabela in (*_CLINICAS_RW, "auditoria"):
        op.execute(f'REVOKE ALL ON TABLE {tabela} FROM "{APP_ROLE}"')
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {tabela}")

    op.drop_table("auditoria")
    op.drop_table("consentimentos")
    op.drop_table("vinculos_resp_paciente")
    op.drop_table("pacientes")
    op.drop_table("responsaveis_legais")
