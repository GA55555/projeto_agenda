import hashlib
import hmac
import uuid

from app.modules.n8n.service import assinatura_hmac, corpo_canonico


def test_corpo_canonico_independe_da_ordem() -> None:
    assert corpo_canonico({"b": 2, "a": "á"}) == corpo_canonico({"a": "á", "b": 2})


def test_assinatura_cobre_timestamp_evento_e_corpo() -> None:
    evento = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    body = b'{"ok":true}'
    esperado = "sha256=" + hmac.new(
        b"segredo", b"123." + str(evento).encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    assert assinatura_hmac(secret="segredo", timestamp="123", evento_id=evento, body=body) == esperado
