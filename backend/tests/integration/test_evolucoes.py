"""Integracao Fase 5: evolucoes sob RLS + gate de consentimento + RAG (§2.2/§3.2/§3.4).

Exercita via API como agenda_app: criar evolucao exige TCLE ativo (§2.2);
chunks sao gerados (§3.3); sem OPENAI_API_KEY os embeddings ficam PENDENTES
(nota persiste, decisao Fase 5); paciente fora do tenant -> 422. Skippa sem BD.
"""
import os
import uuid

import pytest

TEN = str(uuid.uuid4())
EMAIL = "psi-evol@teste.local"
SENHA = "SenhaEvol!"


def _admin_dsn() -> str:
    return (
        f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
        f"port={os.getenv('POSTGRES_PORT', '5432')} "
        f"dbname={os.getenv('POSTGRES_DB', 'agenda')} "
        f"user={os.getenv('POSTGRES_USER', 'agenda_admin')} "
        f"password={os.getenv('POSTGRES_PASSWORD', '')}"
    )


@pytest.fixture
def cenario():
    """Seed committed (tenant+usuario+paciente+TCLE) via API. Yields helpers."""
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
        cur.execute("DELETE FROM evolucao_chunks WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM evolucoes WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM consentimentos WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM vinculos_resp_paciente WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM pacientes WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM responsaveis_legais WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM usuarios WHERE tenant_id=%s", (TEN,))
        cur.execute("DELETE FROM tenants WHERE id=%s", (TEN,))

    _limpa()
    cur.execute("INSERT INTO tenants (id, nome, slug) VALUES (%s,'Evol','evol-psi')", (TEN,))
    cur.execute(
        "INSERT INTO usuarios (tenant_id, email, senha_hash, nome, papel) "
        "VALUES (%s,%s,%s,'Psi','psicologa')",
        (TEN, EMAIL, hash_password(SENHA)),
    )

    client = TestClient(app)
    tok = client.post(
        "/api/v1/auth/login", data={"username": EMAIL, "password": SENHA}
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    resp_id = client.post(
        "/api/v1/responsaveis", headers=h, json={"nome": "Mae Evol", "cpf": "98765432100"}
    ).json()["id"]
    pac_id = client.post(
        "/api/v1/pacientes",
        headers=h,
        json={
            "nome": "Crianca Evol",
            "data_nascimento": "2015-06-01",
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
        yield client, h, pac_id, cur
    finally:
        _limpa()
        conn.close()


def test_criar_evolucao_com_consentimento_gera_chunks(cenario):
    client, h, pac_id, _cur = cenario
    r = client.post(
        "/api/v1/evolucoes",
        headers=h,
        json={"paciente_id": pac_id, "texto": "Sessao boa.\n\nBrincou com o Pedro sem crise."},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total_chunks"] == 2
    # Sem OPENAI_API_KEY no ambiente de teste -> embeddings pendentes (nota persiste).
    assert body["embeddings_pendentes"] == body["total_chunks"]
    assert body["texto"].startswith("Sessao boa")  # nota CRUA preservada (sob RLS)


def test_evolucao_sem_consentimento_ativo_e_bloqueada(cenario):
    client, h, pac_id, cur = cenario
    # Revoga o TCLE do paciente diretamente (simula consentimento revogado, §2.2).
    cur.execute(
        "UPDATE consentimentos SET revogado_em=now() WHERE tenant_id=%s AND paciente_id=%s",
        (TEN, pac_id),
    )
    r = client.post(
        "/api/v1/evolucoes",
        headers=h,
        json={"paciente_id": pac_id, "texto": "Nao deveria gravar."},
    )
    assert r.status_code == 422
    assert "consentimento" in r.text.lower()


def test_paciente_fora_do_tenant_e_422(cenario):
    client, h, _pac_id, _cur = cenario
    r = client.post(
        "/api/v1/evolucoes",
        headers=h,
        json={"paciente_id": str(uuid.uuid4()), "texto": "x"},
    )
    assert r.status_code == 422


def test_listar_evolucoes_do_paciente(cenario):
    client, h, pac_id, _cur = cenario
    client.post(
        "/api/v1/evolucoes", headers=h, json={"paciente_id": pac_id, "texto": "Primeira nota."}
    )
    r = client.get(f"/api/v1/evolucoes?paciente_id={pac_id}", headers=h)
    assert r.status_code == 200
    assert len(r.json()) >= 1
