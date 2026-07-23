"""Prova de isolamento e menor privilegio dos metadados documentais (Fase 7k)."""
import pytest
from psycopg.errors import InsufficientPrivilege

T1 = "10000000-0000-0000-0000-000000000001"
T2 = "10000000-0000-0000-0000-000000000002"
U1 = "11000000-0000-0000-0000-000000000001"
U2 = "11000000-0000-0000-0000-000000000002"
P1 = "12000000-0000-0000-0000-000000000001"
P2 = "12000000-0000-0000-0000-000000000002"
D1 = "13000000-0000-0000-0000-000000000001"
D2 = "13000000-0000-0000-0000-000000000002"


def test_documentos_rls_fail_closed_e_sem_delete(admin_conn):
    cur = admin_conn.cursor()
    cur.execute(
        "INSERT INTO tenants (id, nome, slug) VALUES (%s, 'Docs T1', 'docs-t1'), "
        "(%s, 'Docs T2', 'docs-t2')",
        (T1, T2),
    )
    cur.execute(
        "INSERT INTO usuarios (id, tenant_id, email, senha_hash, nome) VALUES "
        "(%s, %s, 'docs-t1@teste.local', 'x', 'U1'), "
        "(%s, %s, 'docs-t2@teste.local', 'x', 'U2')",
        (U1, T1, U2, T2),
    )
    cur.execute(
        "INSERT INTO pacientes (id, tenant_id, nome, data_nascimento) VALUES "
        "(%s, %s, 'P1', '2020-01-01'), (%s, %s, 'P2', '2020-01-01')",
        (P1, T1, P2, T2),
    )
    cur.execute(
        "INSERT INTO documentos_paciente "
        "(id, tenant_id, paciente_id, enviado_por_usuario_id, nome_original, "
        "chave_armazenamento, tipo_mime, extensao, sha256, tamanho_bytes) VALUES "
        "(%s, %s, %s, %s, 't1.pdf', 'aa/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.pdf', "
        "'application/pdf', '.pdf', %s, 10), "
        "(%s, %s, %s, %s, 't2.pdf', 'bb/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.pdf', "
        "'application/pdf', '.pdf', %s, 10)",
        (D1, T1, P1, U1, "a" * 64, D2, T2, P2, U2, "b" * 64),
    )

    cur.execute("SET ROLE agenda_app")
    cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (T1,))
    cur.execute("SELECT id::text FROM documentos_paciente")
    assert cur.fetchall() == [(D1,)]

    cur.execute("SELECT set_config('app.current_tenant_id', '', true)")
    cur.execute("SELECT count(*) FROM documentos_paciente")
    assert cur.fetchone()[0] == 0

    cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (T1,))
    with pytest.raises(InsufficientPrivilege):
        cur.execute("DELETE FROM documentos_paciente WHERE id = %s", (D1,))
    admin_conn.rollback()
