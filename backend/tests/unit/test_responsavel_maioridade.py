"""Validacao de maioridade do responsavel legal (Fase 7e, §2.2), sem BD."""
from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.modules.responsaveis.schemas import ResponsavelCreate

BASE = {"nome": "Ana Souza", "cpf": "11122233344"}


def _nascimento_ha(anos: int, dias_extra: int = 0) -> date:
    hoje = date.today()
    try:
        alvo = hoje.replace(year=hoje.year - anos)
    except ValueError:
        alvo = hoje.replace(year=hoje.year - anos, day=28)
    return alvo + timedelta(days=dias_extra)


def test_maior_de_idade_aceito():
    r = ResponsavelCreate(**BASE, data_nascimento=_nascimento_ha(30))
    assert r.data_nascimento is not None


def test_exatos_18_anos_aceito():
    # Quem completa 18 hoje ja e maior de idade.
    ResponsavelCreate(**BASE, data_nascimento=_nascimento_ha(18))


def test_menor_de_18_rejeitado():
    with pytest.raises(ValidationError):
        ResponsavelCreate(**BASE, data_nascimento=_nascimento_ha(18, dias_extra=1))


def test_menor_obvio_rejeitado():
    with pytest.raises(ValidationError):
        ResponsavelCreate(**BASE, data_nascimento=_nascimento_ha(10))


def test_sem_data_continua_opcional():
    r = ResponsavelCreate(**BASE)
    assert r.data_nascimento is None
