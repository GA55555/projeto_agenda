"""Cadencia e encerramento da recorrencia, sem PostgreSQL."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.modules.agendamentos.exceptions import TransicaoInvalida
from app.modules.agendamentos.service import _add_meses, _ocorrencia, apagar_recorrencia_futura

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


@patch("app.modules.audit.service.registrar_evento")
def test_apagar_recorrencia_futura_inclui_ocorrencia_aberta(registrar_evento):
    serie_id = uuid.uuid4()
    agendamento_id = uuid.uuid4()
    ag = SimpleNamespace(
        id=agendamento_id,
        serie_id=serie_id,
        status="agendado",
        inicio=datetime.now(timezone.utc) + timedelta(days=1),
    )
    selecao = MagicMock()
    selecao.scalar_one_or_none.return_value = ag
    exclusao = MagicMock()
    exclusao.rowcount = 4
    db = MagicMock()
    db.execute.side_effect = [selecao, exclusao, MagicMock()]
    user = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())

    removidos = apagar_recorrencia_futura(db, user, agendamento_id)

    assert removidos == 4
    assert db.execute.call_count == 3
    assert db.execute.call_args_list[0].args[0]._for_update_arg is not None
    delete_sql = str(db.execute.call_args_list[1].args[0])
    assert "agendamentos.id !=" not in delete_sql  # inclui a ocorrencia aberta
    assert "agendamentos.status" in delete_sql
    assert "agendamentos.inicio >=" in delete_sql  # preserva historico passado
    registrar_evento.assert_called_once()
    assert registrar_evento.call_args.kwargs["payload"] == {
        "serie_id": str(serie_id),
        "removidos": 4,
    }


def test_apagar_recorrencia_futura_recusa_ocorrencia_passada():
    ag = SimpleNamespace(
        serie_id=uuid.uuid4(),
        status="agendado",
        inicio=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = ag

    with pytest.raises(TransicaoInvalida, match="ocorrencia futura"):
        apagar_recorrencia_futura(
            db,
            SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4()),
            uuid.uuid4(),
        )

    assert db.execute.call_count == 1
