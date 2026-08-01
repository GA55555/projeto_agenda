import hashlib
import hmac
import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace

from app.modules.n8n.service import (
    assinatura_hmac,
    corpo_canonico,
    montar_payload_documental,
)


def test_corpo_canonico_independe_da_ordem() -> None:
    assert corpo_canonico({"b": 2, "a": "á"}) == corpo_canonico({"a": "á", "b": 2})


def test_assinatura_cobre_timestamp_evento_e_corpo() -> None:
    evento = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    body = b'{"ok":true}'
    esperado = "sha256=" + hmac.new(
        b"segredo", b"123." + str(evento).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    assert (
        assinatura_hmac(secret="segredo", timestamp="123", evento_id=evento, body=body)
        == esperado
    )


def test_payload_documental_v1_e_minimo() -> None:
    ids = [uuid.UUID(int=i) for i in range(1, 6)]
    instante = datetime(2026, 7, 31, 14, 30, tzinfo=UTC)
    payload = montar_payload_documental(
        evento=SimpleNamespace(id=ids[0]),
        evolucao=SimpleNamespace(id=ids[1], assinada_em=instante, texto="Evolução fiel."),
        paciente=SimpleNamespace(
            id=ids[2], nome="Paciente Teste", data_nascimento=date(2015, 1, 2)
        ),
        agendamento=SimpleNamespace(id=ids[3], inicio=instante, fim=instante.replace(hour=15)),
        assinante=SimpleNamespace(id=ids[4], nome="Psicóloga Teste", crp="06/123456"),
    )

    assert payload["contrato_versao"] == 1
    assert payload["documento_tipo"] == "registro_evolucao_prontuario_psicologico"
    assert payload["texto"] == "Evolução fiel."
    assert set(payload) == {
        "evento_id", "tipo", "contrato_versao", "documento_tipo", "evolucao_id",
        "assinada_em", "texto", "paciente", "atendimento", "psicologa",
    }
    assert set(payload["paciente"]) == {"id", "nome", "data_nascimento"}
    assert set(payload["atendimento"]) == {"id", "inicio", "fim"}
    assert set(payload["psicologa"]) == {"id", "nome", "crp"}
