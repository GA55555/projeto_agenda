"""Regras de arquivamento da Fase 7i, sem PostgreSQL."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.modules.agendamentos.exceptions import TransicaoInvalida
from app.modules.agendamentos.schemas import AgendamentoUpdate
from app.modules.agendamentos.service import _paciente_ativo_para_agendar, atualizar
from app.modules.pacientes.exceptions import PacienteComAgendamentosFuturos
from app.modules.pacientes.models import Paciente
from app.modules.pacientes.service import arquivar, reativar


def _paciente(*, ativo: bool = True) -> Paciente:
    return Paciente(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        nome="Crianca",
        ativo=ativo,
        arquivado_em=None,
        arquivado_por_usuario_id=None,
        motivo_arquivamento=None,
    )


def _user(tenant_id: uuid.UUID):
    return SimpleNamespace(id=uuid.uuid4(), tenant_id=tenant_id)


def _db_para_arquivar(paciente: Paciente, futuras: int) -> MagicMock:
    db = MagicMock()
    paciente_result = MagicMock()
    paciente_result.scalar_one_or_none.return_value = paciente
    futuras_result = MagicMock()
    futuras_result.scalar_one.return_value = futuras
    db.execute.side_effect = [paciente_result, futuras_result]
    return db


def test_arquivar_bloqueia_agendamentos_futuros():
    paciente = _paciente()
    db = _db_para_arquivar(paciente, 2)

    with pytest.raises(PacienteComAgendamentosFuturos) as exc:
        arquivar(db, _user(paciente.tenant_id), paciente.id, None)

    assert exc.value.quantidade == 2
    assert paciente.ativo is True
    db.flush.assert_not_called()


def test_agendamento_exige_paciente_ativo_e_trava_a_linha():
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None

    assert _paciente_ativo_para_agendar(db, uuid.uuid4()) is False

    stmt = db.execute.call_args.args[0]
    assert stmt._for_update_arg is not None
    assert "pacientes.ativo IS true" in str(stmt)


def test_reagendamento_futuro_bloqueia_paciente_arquivado():
    agora = datetime.now(timezone.utc)
    agendamento = SimpleNamespace(
        paciente_id=uuid.uuid4(),
        status="realizado",
        inicio=agora - timedelta(days=1),
        fim=agora - timedelta(days=1) + timedelta(hours=1),
    )
    db = MagicMock()
    db.get.return_value = agendamento
    db.execute.return_value.scalar_one_or_none.return_value = None
    dados = AgendamentoUpdate(
        inicio=agora + timedelta(days=1),
        fim=agora + timedelta(days=1, hours=1),
        status="agendado",
    )

    with pytest.raises(TransicaoInvalida, match="paciente arquivado"):
        atualizar(db, uuid.uuid4(), dados)

    stmt = db.execute.call_args.args[0]
    assert stmt._for_update_arg is not None
    db.flush.assert_not_called()


@patch("app.modules.audit.service.registrar_evento")
def test_arquivar_registra_metadados_e_auditoria(registrar_evento):
    paciente = _paciente()
    user = _user(paciente.tenant_id)
    db = _db_para_arquivar(paciente, 0)

    resultado = arquivar(db, user, paciente.id, "  alta administrativa  ")

    assert resultado is paciente
    assert paciente.ativo is False
    assert paciente.arquivado_por_usuario_id == user.id
    assert paciente.motivo_arquivamento == "alta administrativa"
    assert paciente.arquivado_em is not None
    registrar_evento.assert_called_once()


@patch("app.modules.audit.service.registrar_evento")
def test_reativar_limpa_metadados(registrar_evento):
    paciente = _paciente(ativo=False)
    paciente.arquivado_em = MagicMock()
    paciente.arquivado_por_usuario_id = uuid.uuid4()
    paciente.motivo_arquivamento = "alta"
    user = _user(paciente.tenant_id)
    db = MagicMock()
    db.get.return_value = paciente

    resultado = reativar(db, user, paciente.id)

    assert resultado is paciente
    assert paciente.ativo is True
    assert paciente.arquivado_em is None
    assert paciente.arquivado_por_usuario_id is None
    assert paciente.motivo_arquivamento is None
    registrar_evento.assert_called_once()
