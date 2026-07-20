"""Fronteiras de tempo do resumo do dashboard (Fase 7c), sem BD.

`_limites` deriva as bordas de hoje/mes/semana a partir de um instante *aware*.
O ponto delicado e o rollover do mes (o 1o dia do mes seguinte nao pode depender
do numero de dias do mes atual).
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.modules.dashboard.service import _limites

TZ = ZoneInfo("America/Sao_Paulo")


def test_limites_dia_e_semana():
    agora = datetime(2026, 7, 20, 14, 30, 15, tzinfo=TZ)
    lim = _limites(agora)
    assert lim["inicio_hoje"] == datetime(2026, 7, 20, 0, 0, tzinfo=TZ)
    assert lim["inicio_amanha"] == datetime(2026, 7, 21, 0, 0, tzinfo=TZ)
    assert lim["daqui_uma_semana"] == agora + timedelta(days=7)
    assert lim["agora"] == agora


def test_limites_mes_normal():
    agora = datetime(2026, 7, 20, 9, 0, tzinfo=TZ)
    lim = _limites(agora)
    assert lim["inicio_mes"] == datetime(2026, 7, 1, 0, 0, tzinfo=TZ)
    assert lim["inicio_prox_mes"] == datetime(2026, 8, 1, 0, 0, tzinfo=TZ)


def test_limites_rollover_dezembro():
    # Dezembro -> proximo mes e janeiro do ano seguinte.
    agora = datetime(2026, 12, 31, 23, 59, tzinfo=TZ)
    lim = _limites(agora)
    assert lim["inicio_mes"] == datetime(2026, 12, 1, 0, 0, tzinfo=TZ)
    assert lim["inicio_prox_mes"] == datetime(2027, 1, 1, 0, 0, tzinfo=TZ)


def test_limites_rollover_fevereiro():
    # Fevereiro (28 dias em 2026) nao pode "vazar" para 1o de marco errado.
    agora = datetime(2026, 2, 15, 12, 0, tzinfo=TZ)
    lim = _limites(agora)
    assert lim["inicio_prox_mes"] == datetime(2026, 3, 1, 0, 0, tzinfo=TZ)
