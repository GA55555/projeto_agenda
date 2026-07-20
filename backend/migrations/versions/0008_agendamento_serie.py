"""Recorrencia de agendamentos: coluna `serie_id` (Fase 7f).

Recorrencia = SERIE MATERIALIZADA: ao marcar recorrencia, o backend cria as
ocorrencias futuras (mesmo horario, cadencia semanal/quinzenal/mensal) como
linhas concretas de `agendamentos`, todas com um `serie_id` comum. Assim o
anti-sobreposicao no motor (EXCLUDE), o gate de evolucao (atendimento realizado)
e os contadores do dashboard continuam por linha — sem "ocorrencia virtual".

`serie_id` e nullable (agendamentos avulsos nao tem serie). Indice
(tenant_id, serie_id) para "desfazer recorrencia" (achar as ocorrencias futuras
da serie) — pre-filtro B-Tree (§3.2). Sem grants novos (a tabela ja tinha
SELECT/INSERT/UPDATE/DELETE, Fase 3.5/7e).

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agendamentos",
        sa.Column("serie_id", pg.UUID(as_uuid=True), nullable=True),
    )
    # Cadencia da serie (semanal/quinzenal/mensal): a REGRA sobrevive para a
    # extensao/renovacao da serie (Fase 8) — nao so o agrupamento.
    op.add_column(
        "agendamentos",
        sa.Column("serie_frequencia", sa.String(length=12), nullable=True),
    )
    op.create_index(
        "ix_agendamentos_tenant_id_serie_id", "agendamentos", ["tenant_id", "serie_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_agendamentos_tenant_id_serie_id", table_name="agendamentos")
    op.drop_column("agendamentos", "serie_frequencia")
    op.drop_column("agendamentos", "serie_id")
