"""Regressões da CLI administrativa de controle de acesso."""
from app import cli


class _Resultado:
    def __init__(self, valor):
        self.valor = valor

    def scalar_one_or_none(self):
        return self.valor


class _Conexao:
    def __init__(self, resultado):
        self.resultado = resultado
        self.parametros = None

    def execute(self, _sql, parametros):
        self.parametros = parametros
        return _Resultado(self.resultado)


class _Begin:
    def __init__(self, conexao):
        self.conexao = conexao

    def __enter__(self):
        return self.conexao

    def __exit__(self, *_args):
        return False


class _Engine:
    def __init__(self, conexao):
        self.conexao = conexao

    def begin(self):
        return _Begin(self.conexao)


def test_suspender_usuario_usa_parametros(monkeypatch):
    conexao = _Conexao("usuario-id")
    monkeypatch.setattr(cli, "create_engine", lambda _url: _Engine(conexao))

    assert cli.definir_usuario_ativo("Psi@Clinica.test", ativo=False) is True
    assert conexao.parametros == {"ativo": False, "email": "Psi@Clinica.test"}


def test_suspender_usuario_inexistente_falha(monkeypatch):
    conexao = _Conexao(None)
    monkeypatch.setattr(cli, "create_engine", lambda _url: _Engine(conexao))

    assert cli.definir_usuario_ativo("ausente@clinica.test", ativo=False) is False
