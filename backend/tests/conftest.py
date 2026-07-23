"""Fixtures compartilhadas dos testes.

Os testes de isolamento sao de integracao: precisam de um PostgreSQL com as
migrations aplicadas e o role `agenda_app` provisionado. Se a BD nao estiver
acessivel (ex.: rodando fora do servidor), o teste e SKIPPADO, nao falha.
"""
import os

# Segredo de teste (deterministico, >=32 bytes) antes de qualquer import de settings.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-0123456789-abcdefghij-KLMNOP")

import pytest


def _admin_dsn() -> str:
    return (
        f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
        f"port={os.getenv('POSTGRES_PORT', '5432')} "
        f"dbname={os.getenv('POSTGRES_DB', 'agenda')} "
        f"user={os.getenv('POSTGRES_USER', 'agenda_admin')} "
        f"password={os.getenv('POSTGRES_PASSWORD', '')} "
        "connect_timeout=3"
    )


@pytest.fixture
def admin_conn():
    """Ligacao com o role admin (agenda_admin). Rollback ao final — sem residuo."""
    psycopg = pytest.importorskip("psycopg")
    try:
        conn = psycopg.connect(_admin_dsn())
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL indisponivel para teste de integracao: {exc}")
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
