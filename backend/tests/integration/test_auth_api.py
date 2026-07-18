"""Integracao: login por JWT + isolamento de tenant PELA API (§2.1).

Semeia (committed) dois tenants + usuarios, faz login em cada e confirma que
`GET /tenants/atual` devolve apenas o proprio tenant. Skippa se a BD nao estiver
acessivel (ex.: rodando fora do servidor).
"""
import os
import uuid

import pytest

T_A = str(uuid.uuid4())
T_B = str(uuid.uuid4())
EMAIL_A = "a@teste.local"
EMAIL_B = "b@teste.local"


def _admin_dsn() -> str:
    return (
        f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
        f"port={os.getenv('POSTGRES_PORT', '5432')} "
        f"dbname={os.getenv('POSTGRES_DB', 'agenda')} "
        f"user={os.getenv('POSTGRES_USER', 'agenda_admin')} "
        f"password={os.getenv('POSTGRES_PASSWORD', '')}"
    )


@pytest.fixture
def seed_dois_tenants():
    psycopg = pytest.importorskip("psycopg")
    from app.core.security import hash_password

    try:
        conn = psycopg.connect(_admin_dsn())
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL indisponivel: {exc}")
    conn.autocommit = True
    cur = conn.cursor()
    # Limpa eventuais residuos e semeia (committed, para a app enxergar).
    cur.execute("DELETE FROM usuarios WHERE email IN (%s, %s)", (EMAIL_A, EMAIL_B))
    cur.execute("DELETE FROM tenants WHERE slug IN ('seed-a', 'seed-b')")
    cur.execute(
        "INSERT INTO tenants (id, nome, slug) VALUES (%s,'Seed A','seed-a'),(%s,'Seed B','seed-b')",
        (T_A, T_B),
    )
    cur.execute(
        "INSERT INTO usuarios (tenant_id, email, senha_hash, nome, papel) "
        "VALUES (%s,%s,%s,'A','psicologa'),(%s,%s,%s,'B','psicologa')",
        (T_A, EMAIL_A, hash_password("senhaA"), T_B, EMAIL_B, hash_password("senhaB")),
    )
    try:
        yield
    finally:
        cur.execute("DELETE FROM usuarios WHERE email IN (%s, %s)", (EMAIL_A, EMAIL_B))
        cur.execute("DELETE FROM tenants WHERE slug IN ('seed-a', 'seed-b')")
        conn.close()


def _login(client, email, senha):
    return client.post("/api/v1/auth/login", data={"username": email, "password": senha})


def test_login_e_isolamento_via_api(seed_dois_tenants):
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    # Login A -> ve apenas o tenant A.
    ra = _login(client, EMAIL_A, "senhaA")
    assert ra.status_code == 200
    tok_a = ra.json()["access_token"]
    va = client.get("/api/v1/tenants/atual", headers={"Authorization": f"Bearer {tok_a}"})
    assert va.status_code == 200 and va.json()["slug"] == "seed-a"

    # Login B -> ve apenas o tenant B.
    tok_b = _login(client, EMAIL_B, "senhaB").json()["access_token"]
    vb = client.get("/api/v1/tenants/atual", headers={"Authorization": f"Bearer {tok_b}"})
    assert vb.status_code == 200 and vb.json()["slug"] == "seed-b"

    # Senha errada -> 401.
    assert _login(client, EMAIL_A, "errada").status_code == 401

    # Sem token -> 401.
    assert client.get("/api/v1/tenants/atual").status_code == 401
