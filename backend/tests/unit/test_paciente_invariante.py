"""Invariante do DoD da Fase 3 (§2.2): impossivel criar paciente sem responsavel
legal e sem TCLE. Imposto ja no schema `PacienteCreate` (unitario, sem BD).
"""
import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.modules.pacientes.schemas import PacienteCreate

RESP = uuid.uuid4()


def _consentimento(responsavel_id=RESP) -> dict:
    return {
        "responsavel_id": str(responsavel_id),
        "finalidade_clinica": "Acompanhamento psicologico do TEA",
        "limitacoes_acesso": "Pais acessam apenas evolucao geral",
        "termo_versao": "v1",
        "termo_texto": "Termo especifico ...",
    }


def _vinculo(responsavel_id=RESP) -> dict:
    return {"responsavel_id": str(responsavel_id), "tipo_vinculo": "mae", "principal": True}


def test_paciente_valido_passa():
    p = PacienteCreate(
        nome="Crianca",
        data_nascimento=date(2016, 5, 1),
        vinculos=[_vinculo()],
        consentimento=_consentimento(),
    )
    assert p.consentimento.responsavel_id == RESP


def test_sem_vinculo_e_rejeitado():
    with pytest.raises(ValidationError):
        PacienteCreate(
            nome="Crianca",
            data_nascimento=date(2016, 5, 1),
            vinculos=[],
            consentimento=_consentimento(),
        )


def test_sem_consentimento_e_rejeitado():
    with pytest.raises(ValidationError):
        PacienteCreate(
            nome="Crianca",
            data_nascimento=date(2016, 5, 1),
            vinculos=[_vinculo()],
        )


def test_tcle_deve_apontar_para_responsavel_vinculado():
    with pytest.raises(ValidationError):
        PacienteCreate(
            nome="Crianca",
            data_nascimento=date(2016, 5, 1),
            vinculos=[_vinculo(RESP)],
            consentimento=_consentimento(uuid.uuid4()),  # outro responsavel
        )


def test_tipo_vinculo_invalido_e_rejeitado():
    with pytest.raises(ValidationError):
        PacienteCreate(
            nome="Crianca",
            data_nascimento=date(2016, 5, 1),
            vinculos=[{"responsavel_id": str(RESP), "tipo_vinculo": "padrasto"}],
            consentimento=_consentimento(),
        )
