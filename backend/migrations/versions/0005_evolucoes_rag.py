"""evolucoes + evolucao_chunks: prontuario clinico e RAG (Fase 5)

Duas tabelas clinicas com `tenant_id` + RLS ENABLE/FORCE + politica
`tenant_isolation` (§2.1/§2.1.1):

- `evolucoes`: nota CRUA e legivel (sistema de registro da psicologa). FK
  composto `(tenant_id, paciente_id)` -> pacientes (link intra-tenant no motor).
- `evolucao_chunks`: blocos da nota (§3.3) + `embedding vector(1536)`. `paciente_id`
  denormalizado para a filtragem hibrida §3.2. FK composto `(tenant_id,
  evolucao_id)` -> evolucoes, ON DELETE CASCADE.

§3.4: o embedding deriva so de texto anonimizado (imposto no service); a coluna
vetorial vive sob o mesmo RLS+FORCE. §3.1: NENHUM indice vetorial — Pesquisa
Exata resolve nesta escala. Indices B-Tree `(tenant_id, paciente_id)` para o
pre-filtro §3.2.

Retencao clinica: grants sem DELETE em `evolucoes` (a nota nao se apaga); o
CASCADE dos chunks so atua se a evolucao for removida por caminho privilegiado.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-19
"""
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql as pg

from app.db.rls import tenant_rls_statements

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = os.environ.get("APP_DB_USER", "agenda_app")
assert APP_ROLE.isidentifier(), f"APP_DB_USER invalido como identificador: {APP_ROLE!r}"


def upgrade() -> None:
    op.create_table(
        "evolucoes",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("paciente_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("autor_usuario_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_evolucoes"),
        # Alvo do FK composto vindo dos chunks (§2.1).
        sa.UniqueConstraint("tenant_id", "id", name="uq_evolucoes_tenant_id_id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "paciente_id"],
            ["pacientes.tenant_id", "pacientes.id"],
            name="fk_evolucoes_paciente",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_evolucoes_tenant_id_paciente_id", "evolucoes", ["tenant_id", "paciente_id"])

    op.create_table(
        "evolucao_chunks",
        sa.Column("id", pg.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("paciente_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("evolucao_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("texto_chunk", sa.Text(), nullable=False),
        # pgvector: nullable (embedding PENDENTE se a OpenAI falhar). §3.1: sem indice.
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_evolucao_chunks"),
        sa.UniqueConstraint(
            "tenant_id", "evolucao_id", "ordem",
            name="uq_evolucao_chunks_tenant_id_evolucao_id_ordem",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "evolucao_id"],
            ["evolucoes.tenant_id", "evolucoes.id"],
            name="fk_evolucao_chunks_evolucao",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_evolucao_chunks_tenant_id_paciente_id",
        "evolucao_chunks",
        ["tenant_id", "paciente_id"],
    )

    # RLS (FORCE) + politica de isolamento (§2.1/§2.1.1) nas duas tabelas.
    for tabela in ("evolucoes", "evolucao_chunks"):
        for stmt in tenant_rls_statements(tabela):
            op.execute(stmt)

    # Grants: leitura/escrita, SEM DELETE (retencao clinica + menor privilegio
    # §2.1.1). `evolucao_chunks` so precisa de UPDATE (re-embed de pendentes); a
    # app nunca apaga notas nem chunks. A remocao por caminho privilegiado
    # (superusuario) nao depende de grant ao role de app.
    op.execute(f'GRANT SELECT, INSERT, UPDATE ON TABLE evolucoes TO "{APP_ROLE}"')
    op.execute(f'GRANT SELECT, INSERT, UPDATE ON TABLE evolucao_chunks TO "{APP_ROLE}"')


def downgrade() -> None:
    for tabela in ("evolucao_chunks", "evolucoes"):
        op.execute(f'REVOKE ALL ON TABLE {tabela} FROM "{APP_ROLE}"')
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {tabela}")
    op.drop_table("evolucao_chunks")
    op.drop_table("evolucoes")
