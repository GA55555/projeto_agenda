"""Maquina de estados do agendamento (Fase 7c), sem BD.

`validar_transicao_status` e pura: cancelado e terminal; entrar em cancelado
so pela rota /cancelar (nunca via PATCH); entre agendado/realizado/falta a
transicao e livre (correcao de apontamento); no-op permitido.
"""
import pytest

from app.modules.agendamentos.exceptions import TransicaoInvalida
from app.modules.agendamentos.service import validar_transicao_status


@pytest.mark.parametrize(
    ("atual", "novo"),
    [
        ("agendado", "realizado"),
        ("agendado", "falta"),
        ("realizado", "falta"),      # correcao de apontamento
        ("falta", "realizado"),      # correcao de apontamento
        ("realizado", "agendado"),   # desfazer apontamento (EXCLUDE revalida)
        ("agendado", "agendado"),    # no-op
        ("cancelado", "cancelado"),  # no-op
    ],
)
def test_transicoes_permitidas(atual: str, novo: str):
    validar_transicao_status(atual, novo)  # nao levanta


@pytest.mark.parametrize(
    ("atual", "novo"),
    [
        ("cancelado", "realizado"),  # reviver cancelado (corromperia agregados)
        ("cancelado", "agendado"),
        ("cancelado", "falta"),
        ("agendado", "cancelado"),   # cancelar so pela rota propria (motivo/soft)
        ("realizado", "cancelado"),
    ],
)
def test_transicoes_bloqueadas(atual: str, novo: str):
    with pytest.raises(TransicaoInvalida):
        validar_transicao_status(atual, novo)
