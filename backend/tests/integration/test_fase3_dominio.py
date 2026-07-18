"""Integracao Fase 3 (§2.1/§2.2): RLS nas tabelas de dominio + auditoria imutavel.

Roda como o role `agenda_app` (SET ROLE) para provar o RLS, e testa o trigger
de imutabilidade da auditoria. Numa transacao com rollback — sem residuo.
Tambem exercita o WRITE PATH real pela API (login -> POST paciente -> revogar),
que passa pelo RLS WITH CHECK, pelos grants e pelos FK compostos sob FORCE RLS.
Skippa se nao houver BD (ex.: fora do servidor).
"""
import os
import uuid

import pytest

T1 = "00000000-0000-0000-0000-0000000000a1"
T2 = "00000000-0000-0000-0000-0000000000a2"

TEN = str(uuid.uuid4())
EMAIL_PSI = "psi-fase3@teste.local"
SENHA_PSI = "SenhaFase3!"


def _admin_dsn() -> str:
    return (
        f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
        f"port={os.getenv('POSTGRES_PORT', '5432')} "
        f"dbname={os.getenv('POSTGRES_DB', 'agenda')} "
        f"user={os.getenv('POSTGRES_USER', 'agenda_admin')} "
        f"password={os.getenv('POSTGRES_PASSWORD', '')}"
    )


def test_rls_isolamento_responsaveis(admin_conn):
    cur = admin_conn.cursor()
    cur.execute(
        "INSERT INTO tenants (id, nome, slug) VALUES (%s,'A3','a3'),(%s,'B3','b3')",
        (T1, T2),
    )
    # Seed como admin (bypass RLS): 1 responsavel por tenant.
    cur.execute(
        "INSERT INTO responsaveis_legais (tenant_id, nome, cpf) "
        "VALUES (%s,'Resp T1','11111111111'),(%s,'Resp T2','22222222222')",
        (T1, T2),
    )

    cur.execute("SET ROLE agenda_app")

    # Contexto T1 -> so ve o responsavel de T1.
    cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (T1,))
    cur.execute("SELECT nome FROM responsaveis_legais")
    assert [r[0] for r in cur.fetchall()] == ["Resp T1"]

    # Contexto T2 -> so ve o de T2.
    cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (T2,))
    cur.execute("SELECT nome FROM responsaveis_legais")
    assert [r[0] for r in cur.fetchall()] == ["Resp T2"]

    # Fail-closed: sem contexto -> zero linhas.
    cur.execute("SELECT set_config('app.current_tenant_id', '', true)")
    cur.execute("SELECT count(*) FROM responsaveis_legais")
    assert cur.fetchone()[0] == 0

    cur.execute("RESET ROLE")
    admin_conn.rollback()


def test_auditoria_update_bloqueado(admin_conn):
    psycopg = pytest.importorskip("psycopg")
    cur = admin_conn.cursor()
    cur.execute("INSERT INTO tenants (id, nome, slug) VALUES (%s,'A3','a3')", (T1,))
    cur.execute(
        "INSERT INTO auditoria (tenant_id, tipo_evento, entidade, entidade_id, ator_usuario_id) "
        "VALUES (%s,'consentimento_revogado','consentimento',%s,%s) RETURNING id",
        (T1, str(uuid.uuid4()), str(uuid.uuid4())),
    )
    aid = cur.fetchone()[0]
    # Trigger BEFORE UPDATE barra ate o dono da tabela (§2.2).
    with pytest.raises(psycopg.errors.RaiseException):
        cur.execute("UPDATE auditoria SET tipo_evento='alterado' WHERE id=%s", (aid,))
    admin_conn.rollback()


def test_auditoria_delete_bloqueado(admin_conn):
    psycopg = pytest.importorskip("psycopg")
    cur = admin_conn.cursor()
    cur.execute("INSERT INTO tenants (id, nome, slug) VALUES (%s,'A3','a3')", (T1,))
    cur.execute(
        "INSERT INTO auditoria (tenant_id, tipo_evento, entidade, entidade_id, ator_usuario_id) "
        "VALUES (%s,'guarda_alterada','vinculo',%s,%s) RETURNING id",
        (T1, str(uuid.uuid4()), str(uuid.uuid4())),
    )
    aid = cur.fetchone()[0]
    with pytest.raises(psycopg.errors.RaiseException):
        cur.execute("DELETE FROM auditoria WHERE id=%s", (aid,))
    admin_conn.rollback()


@pytest.fixture
def seed_psicologa():
    """Seed committed (tenant + usuario) para exercitar a API como agenda_app."""
    psycopg = pytest.importorskip("psycopg")
    from app.core.security import hash_password

    try:
        conn = psycopg.connect(_admin_dsn())
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL indisponivel: {exc}")
    conn.autocommit = True
    cur = conn.cursor()

    def _limpa():
        # Remove residuo em ordem segura (FK RESTRICT); auditoria via TRUNCATE-like
        # nao aplica — usamos o proprio DELETE (o trigger so barra UPDATE/DELETE de
        # linha; como admin/owner o DELETE tambem e barrado -> desabilita trigger).
        cur.execute("ALTER TABLE auditoria DISABLE TRIGGER trg_auditoria_imutavel")
        cur.execute("DELETE FROM auditoria WHERE tenant_id=%s", (TEN,))
        cur.execute("ALTER TABLE auditoria ENABLE TRIGGER trg_auditoria_imutavel")
        cur.execute("DELETE FROM consentimentos WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM vinculos_resp_paciente WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM pacientes WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM responsaveis_legais WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM usuarios WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM tenants WHERE id=%s", (TEN,))

    _limpa()
    cur.execute("INSERT INTO tenants (id, nome, slug) VALUES (%s,'Fase3','fase3-psi')", (TEN,))
    cur.execute(
        "INSERT INTO usuarios (tenant_id, email, senha_hash, nome, papel) "
        "VALUES (%s,%s,%s,'Psi','psicologa')",
        (TEN, EMAIL_PSI, hash_password(SENHA_PSI)),
    )
    try:
        yield
    finally:
        _limpa()
        conn.close()


def test_write_path_completo_via_api(seed_psicologa):
    """Login -> cria responsavel -> cria paciente+TCLE -> revoga -> auditoria.

    Cobre o RLS WITH CHECK (INSERT), os grants e os FK compostos sob FORCE RLS.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    tok = client.post(
        "/api/v1/auth/login", data={"username": EMAIL_PSI, "password": SENHA_PSI}
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    # 1) Responsavel legal.
    rr = client.post(
        "/api/v1/responsaveis",
        headers=h,
        json={"nome": "Mae Teste", "cpf": "111.222.333-44"},
    )
    assert rr.status_code == 201, rr.text
    assert rr.json()["cpf"] == "11122233344"  # normalizado (#6)
    resp_id = rr.json()["id"]

    # 2) Paciente + vinculo + TCLE (invariante §2.2, transacao unica).
    rp = client.post(
        "/api/v1/pacientes",
        headers=h,
        json={
            "nome": "Crianca Teste",
            "data_nascimento": "2016-03-10",
            "vinculos": [{"responsavel_id": resp_id, "tipo_vinculo": "mae", "principal": True}],
            "consentimento": {
                "responsavel_id": resp_id,
                "finalidade_clinica": "Acompanhamento do TEA",
                "limitacoes_acesso": "Pais: apenas evolucao geral",
                "termo_versao": "v1",
                "termo_texto": "Termo especifico...",
            },
        },
    )
    assert rp.status_code == 201, rp.text
    corpo = rp.json()
    # #1: a resposta traz os vinculos (nao vazia) com o responsavel aninhado.
    assert len(corpo["vinculos"]) == 1
    assert corpo["vinculos"][0]["responsavel"]["id"] == resp_id
    pac_id = corpo["id"]

    # 3) Consentimento consultavel e revogavel.
    cs = client.get(f"/api/v1/consentimentos?paciente_id={pac_id}", headers=h)
    assert cs.status_code == 200 and len(cs.json()) == 1
    cons_id = cs.json()[0]["id"]

    rev = client.post(f"/api/v1/consentimentos/{cons_id}/revogar", headers=h, json={"motivo": "teste"})
    assert rev.status_code == 200 and rev.json()["revogado_em"] is not None

    # 4) Revogacao gera evento imutavel em auditoria.
    aud = client.get("/api/v1/auditoria?entidade=consentimento", headers=h)
    assert aud.status_code == 200
    assert any(e["tipo_evento"] == "consentimento_revogado" for e in aud.json())

    # 5) Revogar de novo -> 409.
    assert client.post(f"/api/v1/consentimentos/{cons_id}/revogar", headers=h, json={}).status_code == 409
