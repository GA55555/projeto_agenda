"""Regressoes da rotacao concorrente da versao de sessao."""

import uuid

from app.modules.auth import service
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import SenhaUpdate


class _Resultado:
    def __init__(self, usuario: Usuario | None):
        self.usuario = usuario

    def scalar_one_or_none(self) -> Usuario | None:
        return self.usuario


class _Sessao:
    def __init__(self, usuario: Usuario | None):
        self.usuario = usuario
        self.statement = None
        self.flush_count = 0

    def execute(self, statement):
        self.statement = statement
        return _Resultado(self.usuario)

    def flush(self) -> None:
        self.flush_count += 1


def _usuario(*, version: int = 4) -> Usuario:
    return Usuario(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="review@teste.local",
        senha_hash="hash-anterior",
        nome="Review",
        papel="psicologa",
        ativo=True,
        session_version=version,
    )


def test_logout_bloqueia_linha_e_incrementa_versao_esperada() -> None:
    usuario = _usuario()
    db = _Sessao(usuario)

    resultado = service.revogar_sessoes(db, usuario.id, 4)

    assert resultado is usuario
    assert usuario.session_version == 5
    assert db.flush_count == 1
    assert db.statement._for_update_arg is not None
    assert "usuarios.session_version" in str(db.statement)


def test_logout_obsoleto_nao_altera_sessao_mais_nova() -> None:
    db = _Sessao(None)

    assert service.revogar_sessoes(db, uuid.uuid4(), 3) is None
    assert db.flush_count == 0
    assert db.statement._for_update_arg is not None


def test_troca_senha_bloqueia_linha_antes_de_rotacionar(monkeypatch) -> None:
    usuario = _usuario()
    db = _Sessao(usuario)
    monkeypatch.setattr(service, "verify_password", lambda *_args: True)
    monkeypatch.setattr(service, "hash_password", lambda _senha: "hash-novo")

    resultado = service.trocar_senha(
        db,
        usuario.id,
        4,
        SenhaUpdate(senha_atual="senha-antiga", senha_nova="senha-nova"),
    )

    assert resultado is usuario
    assert usuario.senha_hash == "hash-novo"
    assert usuario.session_version == 5
    assert db.statement._for_update_arg is not None
