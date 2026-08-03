"""Regressao: respostas da API sensivel nao podem ser armazenadas em cache."""

from fastapi.testclient import TestClient

from app.main import app


def test_api_declara_no_store_tambem_em_resposta_de_erro() -> None:
    response = TestClient(app).get("/api/v1/rota-inexistente")

    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store, private"


def test_healthcheck_publico_nao_recebe_politica_clinica() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert "cache-control" not in response.headers
