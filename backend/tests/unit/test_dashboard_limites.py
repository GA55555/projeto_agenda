"""Fronteiras de tempo do resumo do dashboard (Fase 7c/7e), sem BD.

`janela_do_dia`/`janela_do_mes` derivam bordas *aware* no fuso da clinica; o
ponto delicado e o rollover do mes (nao pode depender do numero de dias).
`parse_mes` valida o seletor historico.
"""
from datetime import date, datetime

import pytest
from zoneinfo import ZoneInfo

from app.modules.dashboard.service import janela_do_dia, janela_do_mes, parse_mes

TZ = ZoneInfo("America/Sao_Paulo")


def test_janela_do_dia():
    inicio, fim = janela_do_dia(date(2026, 7, 20), TZ)
    assert inicio == datetime(2026, 7, 20, 0, 0, tzinfo=TZ)
    assert fim == datetime(2026, 7, 21, 0, 0, tzinfo=TZ)


def test_janela_do_mes_normal():
    inicio, fim = janela_do_mes(2026, 7, TZ)
    assert inicio == datetime(2026, 7, 1, 0, 0, tzinfo=TZ)
    assert fim == datetime(2026, 8, 1, 0, 0, tzinfo=TZ)


def test_janela_do_mes_rollover_dezembro():
    inicio, fim = janela_do_mes(2026, 12, TZ)
    assert inicio == datetime(2026, 12, 1, 0, 0, tzinfo=TZ)
    assert fim == datetime(2027, 1, 1, 0, 0, tzinfo=TZ)


def test_janela_do_mes_rollover_fevereiro():
    _, fim = janela_do_mes(2026, 2, TZ)
    assert fim == datetime(2026, 3, 1, 0, 0, tzinfo=TZ)


def test_parse_mes_valido():
    assert parse_mes("2026-07") == (2026, 7)
    assert parse_mes("2025-12") == (2025, 12)


@pytest.mark.parametrize("valor", ["2026-13", "2026-00", "2026", "julho", "2026-7x"])
def test_parse_mes_invalido(valor: str):
    with pytest.raises(ValueError):
        parse_mes(valor)
