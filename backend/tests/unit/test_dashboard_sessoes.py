"""Mini-dashboard administrativo de sessoes (Fase 7j), sem PostgreSQL."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.modules.dashboard.service import (
    _intervalo_mediano_dias,
    montar_resumo_sessoes_paciente,
)


def _ag(*, inicio: datetime, status: str, tipo: str = "sessao"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        inicio=inicio,
        fim=inicio + timedelta(minutes=50),
        status=status,
        tipo=tipo,
        serie_id=None,
    )


def test_intervalo_mediano_dias():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert _intervalo_mediano_dias([base + timedelta(days=21), base + timedelta(days=7), base]) == 10.5
    assert _intervalo_mediano_dias([base]) is None


def test_resumo_inexistente_para_paciente_fora_do_contexto_rls():
    db = MagicMock()
    db.execute.return_value.one_or_none.return_value = None

    assert montar_resumo_sessoes_paciente(db, uuid.uuid4()) is None
    assert db.execute.call_count == 1


def test_montar_resumo_sessoes_mapeia_indicadores_e_historico():
    agora = datetime.now(timezone.utc)
    paciente_id = uuid.uuid4()
    evolucao_id = uuid.uuid4()
    realizada_mais_recente = _ag(inicio=agora - timedelta(days=7), status="realizado")
    realizada_anterior = _ag(inicio=agora - timedelta(days=21), status="realizado")
    proxima = _ag(inicio=agora + timedelta(days=7), status="agendado")

    paciente_result = MagicMock()
    paciente_result.one_or_none.return_value = SimpleNamespace(ativo=True)
    contadores_result = MagicMock()
    contadores_result.one.return_value = (8, 2, 1, 6, 2)
    realizadas_result = MagicMock()
    realizadas_result.all.return_value = [
        (realizada_mais_recente, evolucao_id),
        (realizada_anterior, None),
    ]
    proxima_result = MagicMock()
    proxima_result.first.return_value = (proxima, None)
    total_result = MagicMock()
    total_result.scalar_one.return_value = 11
    historico_result = MagicMock()
    historico_result.all.return_value = [
        (proxima, None),
        (realizada_mais_recente, evolucao_id),
    ]
    db = MagicMock()
    db.execute.side_effect = [
        paciente_result,
        contadores_result,
        realizadas_result,
        proxima_result,
        total_result,
        historico_result,
    ]

    resumo = montar_resumo_sessoes_paciente(db, paciente_id, limite=10, offset=0)

    assert resumo is not None
    assert resumo.total_realizadas == 8
    assert resumo.realizadas_mes_atual == 2
    assert resumo.realizadas_ano_atual == 6
    assert resumo.faltas_total == 2
    assert resumo.cancelamentos_total == 1
    assert resumo.taxa_comparecimento == 0.8
    assert resumo.ultima_sessao.id == realizada_mais_recente.id
    assert resumo.ultima_sessao.evolucao_id == evolucao_id
    assert resumo.proxima_sessao.id == proxima.id
    assert resumo.intervalo_mediano_dias == 14.0
    assert resumo.historico_total == 11
    assert len(resumo.historico) == 2
