"""Validacao dos schemas de perfil (Fase 7c), sem BD."""
import pytest
from pydantic import ValidationError

from app.modules.auth.schemas import PerfilUpdate, SenhaUpdate


def test_perfil_parcial_so_nome():
    p = PerfilUpdate(nome="Dra. Ana")
    # Enviou so nome -> email fica fora do dump (nao vira null no PATCH).
    assert p.model_dump(exclude_unset=True) == {"nome": "Dra. Ana"}


def test_perfil_email_normalizado_minusculo():
    # Lowercase TOTAL (nao so o dominio do EmailStr): o e-mail e identificador
    # de login — case preservado trancaria a conta e burlaria o UNIQUE.
    p = PerfilUpdate(email="ANA@Clinica.com")
    assert p.email == "ana@clinica.com"


def test_perfil_email_invalido_rejeitado():
    with pytest.raises(ValidationError):
        PerfilUpdate(email="sem-arroba")


def test_perfil_nome_null_explicito_rejeitado():
    with pytest.raises(ValidationError):
        PerfilUpdate(nome=None)


def test_perfil_vazio_ok():
    # Nada enviado e valido (o service simplesmente nao altera nada).
    assert PerfilUpdate().model_dump(exclude_unset=True) == {}


def test_senha_nova_curta_rejeitada():
    with pytest.raises(ValidationError):
        SenhaUpdate(senha_atual="atual123", senha_nova="curta")


def test_senha_valida():
    s = SenhaUpdate(senha_atual="atual123", senha_nova="NovaSenha123")
    assert s.senha_nova == "NovaSenha123"


def test_senha_atual_vazia_rejeitada():
    with pytest.raises(ValidationError):
        SenhaUpdate(senha_atual="", senha_nova="NovaSenha123")


def test_senha_acima_de_72_bytes_rejeitada():
    # 40 x 'ã' = 40 chars mas 80 bytes UTF-8: passa no max_length de chars,
    # mas estoura o limite de 72 BYTES do bcrypt (>=5 levanta ValueError).
    with pytest.raises(ValidationError):
        SenhaUpdate(senha_atual="atual123", senha_nova="ã" * 40)


def test_senha_72_bytes_exatos_aceita():
    s = SenhaUpdate(senha_atual="atual123", senha_nova="a" * 72)
    assert len(s.senha_nova.encode("utf-8")) == 72


def test_perfil_senha_atual_nao_e_campo_gravavel():
    # senha_atual acompanha a troca de e-mail (re-auth), mas nunca pode vazar
    # para o loop de setattr do service como se fosse coluna.
    p = PerfilUpdate(email="ana@clinica.com", senha_atual="minhasenha")
    campos = p.model_dump(exclude_unset=True)
    campos.pop("senha_atual", None)
    assert campos == {"email": "ana@clinica.com"}
