"""Testes da extração de token e revogação de sessão — Fase 7/Manutenção.

Sem BD: exercita as dependências com Request falso, JWT real e verificação da
conta substituída por mock (o segredo de teste vem do conftest).

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 7
"""
import uuid

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import create_access_token
from app.modules.auth.dependencies import CurrentUser, _extrair_token, get_current_user


class _FakeReq:
    def __init__(self, cookies=None, headers=None):
        self.cookies = cookies or {}
        self.headers = headers or {}


def test_token_do_cookie():
    req = _FakeReq(cookies={settings.cookie_name: "abc"})
    assert _extrair_token(req) == "abc"


def test_token_do_header_bearer():
    req = _FakeReq(headers={"Authorization": "Bearer xyz"})
    assert _extrair_token(req) == "xyz"


def test_cookie_tem_prioridade_sobre_header():
    req = _FakeReq(
        cookies={settings.cookie_name: "do-cookie"},
        headers={"Authorization": "Bearer do-header"},
    )
    assert _extrair_token(req) == "do-cookie"


def test_sem_token_retorna_none():
    assert _extrair_token(_FakeReq()) is None


def test_get_current_user_valida_jwt_do_cookie(monkeypatch):
    uid, tid = uuid.uuid4(), uuid.uuid4()
    token = create_access_token(user_id=uid, tenant_id=tid, papel="psicologa")
    monkeypatch.setattr(
        "app.modules.auth.dependencies._conta_continua_ativa", lambda _user: True
    )
    user = get_current_user(_FakeReq(cookies={settings.cookie_name: token}))
    assert isinstance(user, CurrentUser)
    assert user.id == uid and user.tenant_id == tid and user.papel == "psicologa"


def test_get_current_user_sem_token_401():
    with pytest.raises(HTTPException) as exc:
        get_current_user(_FakeReq())
    assert exc.value.status_code == 401


def test_get_current_user_revoga_jwt_de_conta_inativa(monkeypatch):
    token = create_access_token(
        user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), papel="psicologa"
    )
    monkeypatch.setattr(
        "app.modules.auth.dependencies._conta_continua_ativa", lambda _user: False
    )

    with pytest.raises(HTTPException) as exc:
        get_current_user(_FakeReq(cookies={settings.cookie_name: token}))

    assert exc.value.status_code == 401
