"""Integracao Fase 3.5: agenda sob RLS + anti-sobreposicao no motor (§2.1).

Exercita, via API como agenda_app: criar agendamento, sobreposicao rejeitada
(409, EXCLUDE), atendimentos encostados (fim==inicio) permitidos, e cancelar
liberando o horario. Skippa se nao houver BD.
"""
import os
import uuid

import pytest

TEN = str(uuid.uuid4())
EMAIL = "psi-agenda@teste.local"
SENHA = "SenhaAgenda!"


def _admin_dsn() -> str:
    return (
        f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
        f"port={os.getenv('POSTGRES_PORT', '5432')} "
        f"dbname={os.getenv('POSTGRES_DB', 'agenda')} "
        f"user={os.getenv('POSTGRES_USER', 'agenda_admin')} "
        f"password={os.getenv('POSTGRES_PASSWORD', '')}"
    )


@pytest.fixture
def seed_e_paciente():
    """Seed committed (tenant+usuario) e retorna (headers, paciente_id) via API."""
    psycopg = pytest.importorskip("psycopg")
    from fastapi.testclient import TestClient

    from app.core.security import hash_password
    from app.main import app

    try:
        conn = psycopg.connect(_admin_dsn())
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL indisponivel: {exc}")
    conn.autocommit = True
    cur = conn.cursor()

    def _limpa():
        cur.execute("DELETE FROM agendamentos WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM consentimentos WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM vinculos_resp_paciente WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM pacientes WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM responsaveis_legais WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM usuarios WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM tenants WHERE id=%s", (TEN,))

    _limpa()
    cur.execute("INSERT INTO tenants (id, nome, slug) VALUES (%s,'Agenda','agenda-psi')", (TEN,))
    cur.execute(
        "INSERT INTO usuarios (tenant_id, email, senha_hash, nome, papel) "
        "VALUES (%s,%s,%s,'Psi','psicologa')",
        (TEN, EMAIL, hash_password(SENHA)),
    )

    client = TestClient(app)
    tok = client.post("/api/v1/auth/login", data={"username": EMAIL, "password": SENHA}).json()[
        "access_token"
    ]
    h = {"Authorization": f"Bearer {tok}"}
    resp_id = client.post("/api/v1/responsaveis", headers=h, json={"nome": "Mae", "cpf": "12345678901"}).json()[
        "id"
    ]
    pac_id = client.post(
        "/api/v1/pacientes",
        headers=h,
        json={
            "nome": "Crianca",
            "data_nascimento": "2016-03-10",
            "vinculos": [{"responsavel_id": resp_id, "tipo_vinculo": "mae", "principal": True}],
            "consentimento": {
                "responsavel_id": resp_id,
                "finalidade_clinica": "TEA",
                "limitacoes_acesso": "geral",
                "termo_versao": "v1",
                "termo_texto": "termo",
            },
        },
    ).json()["id"]

    try:
        yield client, h, pac_id
    finally:
        _limpa()
        conn.close()


def _ag(pac_id, inicio, fim, **extra):
    return {"paciente_id": pac_id, "inicio": inicio, "fim": fim, **extra}


def test_agenda_sobreposicao_e_cancelamento(seed_e_paciente):
    client, h, pac_id = seed_e_paciente

    # 14:00-15:00 -> ok
    r1 = client.post("/api/v1/agendamentos", headers=h,
                     json=_ag(pac_id, "2026-08-01T14:00:00-03:00", "2026-08-01T15:00:00-03:00"))
    assert r1.status_code == 201, r1.text
    ag1 = r1.json()["id"]

    # 14:30-15:30 -> sobrepoe -> 409 (EXCLUDE no motor, §2.1)
    r2 = client.post("/api/v1/agendamentos", headers=h,
                     json=_ag(pac_id, "2026-08-01T14:30:00-03:00", "2026-08-01T15:30:00-03:00"))
    assert r2.status_code == 409, r2.text

    # 15:00-16:00 -> encostado (fim==inicio) -> permitido ('[)')
    r3 = client.post("/api/v1/agendamentos", headers=h,
                     json=_ag(pac_id, "2026-08-01T15:00:00-03:00", "2026-08-01T16:00:00-03:00"))
    assert r3.status_code == 201, r3.text
    ag3 = r3.json()["id"]

    # PATCH parcial que inverte o intervalo (so `fim`) -> 422 (nao 500).
    rp = client.patch(f"/api/v1/agendamentos/{ag3}", headers=h,
                      json={"fim": "2026-08-01T14:30:00-03:00"})
    assert rp.status_code == 422, rp.text

    # cancela o 1o -> libera 14:00-15:00
    rc = client.post(f"/api/v1/agendamentos/{ag1}/cancelar", headers=h, json={"motivo": "teste"})
    assert rc.status_code == 200 and rc.json()["status"] == "cancelado"

    # agora 14:00-15:00 volta a ser possivel
    r4 = client.post("/api/v1/agendamentos", headers=h,
                     json=_ag(pac_id, "2026-08-01T14:00:00-03:00", "2026-08-01T15:00:00-03:00"))
    assert r4.status_code == 201, r4.text

    # paciente inexistente -> 422
    r5 = client.post("/api/v1/agendamentos", headers=h,
                     json=_ag(str(uuid.uuid4()), "2026-08-02T10:00:00-03:00", "2026-08-02T11:00:00-03:00"))
    assert r5.status_code == 422, r5.text

    # listagem traz os 2 ativos (1o cancelado nao conta se filtrar status)
    ativos = client.get("/api/v1/agendamentos?status=agendado", headers=h).json()
    assert len(ativos) == 2


def test_rls_isolamento_agendamentos(admin_conn):
    """T1 so ve a agenda de T1; sem contexto -> vazio (fail-closed), §2.1."""
    t1 = "00000000-0000-0000-0000-0000000000b1"
    t2 = "00000000-0000-0000-0000-0000000000b2"
    cur = admin_conn.cursor()
    # Seed como admin (superusuario ignora RLS): tenant -> paciente -> agendamento.
    cur.execute("INSERT INTO tenants (id, nome, slug) VALUES (%s,'B1','vb1'),(%s,'B2','vb2')", (t1, t2))
    cur.execute(
        "INSERT INTO pacientes (id, tenant_id, nome, data_nascimento) "
        "VALUES (%s,%s,'PA','2016-01-01'),(%s,%s,'PB','2016-01-01')",
        (t1, t1, t2, t2),  # reusa o proprio id do tenant como id do paciente (ok p/ teste)
    )
    cur.execute(
        "INSERT INTO agendamentos (tenant_id, paciente_id, inicio, fim) VALUES "
        "(%s,%s,'2026-08-01T14:00-03','2026-08-01T15:00-03'),"
        "(%s,%s,'2026-08-01T14:00-03','2026-08-01T15:00-03')",
        (t1, t1, t2, t2),
    )

    cur.execute("SET ROLE agenda_app")
    cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (t1,))
    cur.execute("SELECT count(*) FROM agendamentos")
    assert cur.fetchone()[0] == 1
    cur.execute("SELECT tenant_id::text FROM agendamentos")
    assert cur.fetchone()[0] == t1

    cur.execute("SELECT set_config('app.current_tenant_id', '', true)")
    cur.execute("SELECT count(*) FROM agendamentos")
    assert cur.fetchone()[0] == 0

    cur.execute("RESET ROLE")
    admin_conn.rollback()
