"""Cadencia da recorrencia de agendamentos (Fase 7f), sem BD."""
from datetime import datetime, timezone

from app.modules.agendamentos.service import _add_meses, _ocorrencia

T = datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc)


def test_semanal_k_esima():
    assert _ocorrencia(T, "semanal", 1) == datetime(2026, 1, 22, 14, 0, tzinfo=timezone.utc)
    assert _ocorrencia(T, "semanal", 3) == datetime(2026, 2, 5, 14, 0, tzinfo=timezone.utc)


def test_quinzenal_k_esima():
    assert _ocorrencia(T, "quinzenal", 1) == datetime(2026, 1, 29, 14, 0, tzinfo=timezone.utc)
    assert _ocorrencia(T, "quinzenal", 2) == datetime(2026, 2, 12, 14, 0, tzinfo=timezone.utc)


def test_mensal_mantem_dia_e_hora():
    assert _ocorrencia(T, "mensal", 1) == datetime(2026, 2, 15, 14, 0, tzinfo=timezone.utc)
    assert _ocorrencia(T, "mensal", 2) == datetime(2026, 3, 15, 14, 0, tzinfo=timezone.utc)


def test_mensal_dia_31_nao_deriva_a_partir_do_anchor():
    # Regressao do drift: cada ocorrencia vem do ANCHOR (dia 31), nao da anterior
    # ja clampada. 31/01 -> 28/02 -> 31/03 -> 30/04 -> 31/05...
    anchor = datetime(2026, 1, 31, 9, 0, tzinfo=timezone.utc)
    assert _ocorrencia(anchor, "mensal", 1) == datetime(2026, 2, 28, 9, 0, tzinfo=timezone.utc)
    assert _ocorrencia(anchor, "mensal", 2) == datetime(2026, 3, 31, 9, 0, tzinfo=timezone.utc)
    assert _ocorrencia(anchor, "mensal", 3) == datetime(2026, 4, 30, 9, 0, tzinfo=timezone.utc)
    assert _ocorrencia(anchor, "mensal", 4) == datetime(2026, 5, 31, 9, 0, tzinfo=timezone.utc)


def test_add_meses_rollover_de_ano():
    d = datetime(2026, 12, 10, 8, 0, tzinfo=timezone.utc)
    assert _add_meses(d, 1) == datetime(2027, 1, 10, 8, 0, tzinfo=timezone.utc)


def test_add_meses_clampa_31_para_fevereiro_bissexto():
    d = datetime(2028, 1, 31, 12, 0, tzinfo=timezone.utc)
    assert _add_meses(d, 1) == datetime(2028, 2, 29, 12, 0, tzinfo=timezone.utc)
