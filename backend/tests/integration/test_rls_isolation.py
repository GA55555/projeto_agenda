"""Teste de isolamento multitenant via RLS (§2.1/§2.1.1).

Prova, agindo como o role `agenda_app` (SET ROLE), que:
  1. com contexto de T1, so se ve T1 (e nunca T2);
  2. fail-closed: sem contexto, nao se ve NADA (nega em vez de vazar).

Roda numa transacao com rollback — nao deixa residuo. Skippa se nao houver BD.
"""
T1 = "00000000-0000-0000-0000-000000000001"
T2 = "00000000-0000-0000-0000-000000000002"


def test_rls_isolation_e_fail_closed(admin_conn):
    cur = admin_conn.cursor()

    # Seed como admin (superusuario ignora RLS por desenho).
    cur.execute(
        "INSERT INTO tenants (id, nome, slug) VALUES (%s, 'T1', 't1'), (%s, 'T2', 't2')",
        (T1, T2),
    )

    # Passa a agir como o role de aplicacao -> RLS imposto.
    cur.execute("SET ROLE agenda_app")

    # 1) Contexto T1 -> apenas T1 visivel.
    cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (T1,))
    cur.execute("SELECT id::text FROM tenants ORDER BY slug")
    assert [r[0] for r in cur.fetchall()] == [T1]

    # 2) Contexto T2 -> apenas T2 visivel.
    cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (T2,))
    cur.execute("SELECT id::text FROM tenants ORDER BY slug")
    assert [r[0] for r in cur.fetchall()] == [T2]

    # 3) Fail-closed: sem contexto -> zero linhas.
    cur.execute("SELECT set_config('app.current_tenant_id', '', true)")
    cur.execute("SELECT count(*) FROM tenants")
    assert cur.fetchone()[0] == 0

    cur.execute("RESET ROLE")
    admin_conn.rollback()
