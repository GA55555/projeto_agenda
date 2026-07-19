"""Validacao de schema dos agendamentos (Fase 3.5), sem BD."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.modules.agendamentos.schemas import AgendamentoCreate, AgendamentoUpdate

T0 = datetime(2026, 8, 1, 14, 0, tzinfo=timezone.utc)
PAC = uuid.uuid4()


def test_create_valido():
    a = AgendamentoCreate(paciente_id=PAC, inicio=T0, fim=T0 + timedelta(hours=1))
    assert a.fim > a.inicio


def test_create_fim_antes_de_inicio_rejeitado():
    with pytest.raises(ValidationError):
        AgendamentoCreate(paciente_id=PAC, inicio=T0, fim=T0 - timedelta(minutes=1))


def test_create_fim_igual_inicio_rejeitado():
    with pytest.raises(ValidationError):
        AgendamentoCreate(paciente_id=PAC, inicio=T0, fim=T0)


def test_update_status_invalido_rejeitado():
    with pytest.raises(ValidationError):
        AgendamentoUpdate(status="remarcado")


def test_update_status_null_explicito_rejeitado():
    with pytest.raises(ValidationError):
        AgendamentoUpdate(status=None)


def test_update_reagendar_ordem_invalida_rejeitada():
    with pytest.raises(ValidationError):
        AgendamentoUpdate(inicio=T0, fim=T0 - timedelta(minutes=1))


def test_update_parcial_ok():
    a = AgendamentoUpdate(status="realizado")
    assert a.status == "realizado" and a.inicio is None
