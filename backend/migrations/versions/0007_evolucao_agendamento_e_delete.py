"""Evolucao vinculada a agendamento + grants de DELETE controlados (Fase 7e).

1) `evolucoes.agendamento_id` (nullable — evolucoes legadas ficam sem vinculo):
   cada evolucao nova e atrelada ao atendimento (agendamento) que a originou; a
   data do atendimento passa a ser a do agendamento. FK COMPOSTO
   `(tenant_id, agendamento_id)` (§2.1: o motor garante mesmo tenant) com
   ON DELETE RESTRICT — um agendamento referenciado por prontuario NAO pode ser
   apagado, nem por bug da app. Exige UNIQUE(tenant_id, id) em `agendamentos`
   (alvo do FK composto).

2) Grants de DELETE (menor privilegio, §2.1.1):
   - `agendamentos`: apagar erro de lancamento (service restringe a status
     'agendado'; o FK acima protege os referenciados).
   - `pacientes`/`vinculos_resp_paciente`/`consentimentos`: apagar paciente SEM
     prontuario (cadastro errado). **`evolucoes`/`evolucao_chunks` seguem SEM
     DELETE**: a guarda de prontuario por 5 anos (CFP 001/2009, §0.3) fica
     garantida NO MOTOR — o role da app e incapaz de apagar prontuario.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-20
"""
import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = os.environ.get("APP_DB_USER", "agenda_app")
assert APP_ROLE.isidentifier(), f"APP_DB_USER invalido como identificador: {APP_ROLE!r}"


def upgrade() -> None:
    # Alvo do FK composto (tenant_id, id) vindo das evolucoes (§2.1).
    op.create_unique_constraint("uq_agendamentos_tenant_id_id", "agendamentos", ["tenant_id", "id"])

    op.add_column(
        "evolucoes",
        sa.Column("agendamento_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_evolucoes_agendamento",
        "evolucoes",
        "agendamentos",
        ["tenant_id", "agendamento_id"],
        ["tenant_id", "id"],
        ondelete="RESTRICT",
    )
    # Lookup do vinculo (join da data de atendimento) — B-Tree simples (§3.2).
    op.create_index("ix_evolucoes_agendamento_id", "evolucoes", ["agendamento_id"])
    # Contagem de evolucoes por mes no dashboard (Fase 7e): pre-filtro B-Tree
    # (tenant_id, criado_em) evita seq scan a cada carga, importante sob a
    # guarda de 5 anos que faz a tabela crescer (§3.2/§0.3).
    op.create_index("ix_evolucoes_tenant_id_criado_em", "evolucoes", ["tenant_id", "criado_em"])

    op.execute(f'GRANT DELETE ON TABLE agendamentos TO "{APP_ROLE}"')
    op.execute(f'GRANT DELETE ON TABLE pacientes TO "{APP_ROLE}"')
    op.execute(f'GRANT DELETE ON TABLE vinculos_resp_paciente TO "{APP_ROLE}"')
    op.execute(f'GRANT DELETE ON TABLE consentimentos TO "{APP_ROLE}"')
    # evolucoes/evolucao_chunks: DELETE deliberadamente NAO concedido (CFP §0.3).


def downgrade() -> None:
    op.execute(f'REVOKE DELETE ON TABLE consentimentos FROM "{APP_ROLE}"')
    op.execute(f'REVOKE DELETE ON TABLE vinculos_resp_paciente FROM "{APP_ROLE}"')
    op.execute(f'REVOKE DELETE ON TABLE pacientes FROM "{APP_ROLE}"')
    op.execute(f'REVOKE DELETE ON TABLE agendamentos FROM "{APP_ROLE}"')
    op.drop_index("ix_evolucoes_tenant_id_criado_em", table_name="evolucoes")
    op.drop_index("ix_evolucoes_agendamento_id", table_name="evolucoes")
    op.drop_constraint("fk_evolucoes_agendamento", "evolucoes", type_="foreignkey")
    op.drop_column("evolucoes", "agendamento_id")
    op.drop_constraint("uq_agendamentos_tenant_id_id", "agendamentos", type_="unique")
