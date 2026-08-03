"""Validacoes fail-fast da configuracao de seguranca."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_recusa_segredo_jwt_curto() -> None:
    segredo_fraco = "segredo-fraco-nao-exibir"

    with pytest.raises(
        ValidationError, match="JWT_SECRET_KEY deve conter ao menos 32 bytes"
    ) as exc:
        Settings(jwt_secret_key=segredo_fraco)

    assert segredo_fraco not in str(exc.value)


def test_recusa_algoritmo_jwt_fora_do_contrato() -> None:
    with pytest.raises(ValidationError, match="JWT_ALGORITHM deve ser HS256"):
        Settings(
            jwt_secret_key="segredo-de-teste-com-mais-de-32-bytes",
            jwt_algorithm="HS512",
        )


def test_aceita_configuracao_jwt_forte_e_hs256() -> None:
    configuracao = Settings(
        jwt_secret_key="segredo-de-teste-com-mais-de-32-bytes",
        jwt_algorithm="HS256",
    )

    assert configuracao.jwt_algorithm == "HS256"
