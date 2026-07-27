"""Contrato explícito da assinatura eletrônica da evolução (Fase 8b)."""
import uuid

import pytest
from pydantic import ValidationError

from app.modules.evolucoes.schemas import EvolucaoCreate


def _payload(**extra):
    return {
        "paciente_id": uuid.uuid4(),
        "agendamento_id": uuid.uuid4(),
        "texto": "Evolução revisada.",
        **extra,
    }


def test_assinatura_exige_confirmacao_explicita():
    with pytest.raises(ValidationError):
        EvolucaoCreate.model_validate(_payload())
    with pytest.raises(ValidationError):
        EvolucaoCreate.model_validate(_payload(confirmar_assinatura=False))


def test_assinatura_aceita_somente_confirmacao_verdadeira():
    dados = EvolucaoCreate.model_validate(_payload(confirmar_assinatura=True))
    assert dados.confirmar_assinatura is True
