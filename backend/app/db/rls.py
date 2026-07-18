"""Fonte unica da politica de Row-Level Security por locatario (§2.1/§2.1.1).

- `tenant_rls_statements`: DDL usada pelas migrations para blindar uma tabela.
- `set_current_tenant`: injeta o contexto do locatario POR TRANSACAO (Fase 2),
  via set_config(..., is_local=true) — equivalente a SET LOCAL, mas parametrizavel
  e imune a injecao. Nunca usar SET (nao-local): o valor vazaria entre requisicoes
  num pool de ligacoes partilhado.

Politica fail-closed: se o GUC nao estiver definido, `nullif(...,'')::uuid` vira
NULL e a comparacao nao casa nenhuma linha -> a consulta devolve VAZIO (nunca tudo).
Assim, esquecer de injetar o contexto nega acesso em vez de vazar dados.

Regras de ouro: §2.1, §2.1.1
Fase do roadmap: Fase 1 (DDL) / Fase 2 (runtime)
"""
from sqlalchemy import text

# Nome do parametro de sessao (GUC) que carrega o locatario ativo.
TENANT_GUC = "app.current_tenant_id"


def tenant_rls_statements(
    table: str,
    *,
    tenant_column: str = "tenant_id",
    policy_name: str = "tenant_isolation",
) -> list[str]:
    """Retorna as instrucoes que ativam RLS + FORCE + politica de isolamento.

    `FORCE` garante que nem o dono da tabela escape a politica (§2.1.1).
    Superusuario continua com bypass por desenho (acesso break-glass).
    """
    predicate = f"{tenant_column} = nullif(current_setting('{TENANT_GUC}', true), '')::uuid"
    return [
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY",
        f"CREATE POLICY {policy_name} ON {table} "
        f"FOR ALL USING ({predicate}) WITH CHECK ({predicate})",
    ]


def set_current_tenant(connection, tenant_id) -> None:
    """Define o locatario ativo apenas para a transacao corrente (Fase 2)."""
    connection.execute(
        text("SELECT set_config(:k, :v, true)"),
        {"k": TENANT_GUC, "v": str(tenant_id)},
    )
