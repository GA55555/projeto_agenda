"""Testes unitarios de seguranca (hash + JWT) — nao precisam de BD."""
import os
import uuid

# Segredo de teste deterministico (>=32 bytes; nao usar em producao).
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-0123456789-abcdefghij-KLMNOP")

import jwt  # noqa: E402
import pytest  # noqa: E402

from app.core.security import (  # noqa: E402
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_verifica_senha_correta_e_rejeita_errada():
    h = hash_password("segredo123")
    assert h != "segredo123"          # nunca em claro
    assert verify_password("segredo123", h) is True
    assert verify_password("errada", h) is False


def test_token_roundtrip_carrega_tenant_e_papel():
    uid, tid = uuid.uuid4(), uuid.uuid4()
    token = create_access_token(user_id=uid, tenant_id=tid, papel="psicologa")
    payload = decode_access_token(token)
    assert payload["sub"] == str(uid)
    assert payload["tenant_id"] == str(tid)
    assert payload["papel"] == "psicologa"


def test_token_invalido_e_rejeitado():
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("nao.e.um.token")
