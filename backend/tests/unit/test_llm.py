"""Testes unitarios da Fase 6: tunel LLM (montagem, guard-rail, desanonimizacao).

OpenAI e mockado; a anonimizacao/desanonimizacao e o guard-rail sao REAIS. Prova:
  - o payload que "sai" nao contem PII crua (so marcadores);
  - a resposta e desanonimizada de volta ao nome real;
  - marcadores consistentes entre nota e historico (uma anonimizacao so);
  - guard-rail aborta ANTES da OpenAI se PII escapar;
  - gate de consentimento (§2.2).

Regras de ouro: §2.3, §3.4
Fase do roadmap: Fase 6
"""
import uuid

import pytest

from app.modules.auth.dependencies import CurrentUser
from app.modules.anonimizacao.automaton import AhoCorasick, respeita_fronteira
from app.modules.anonimizacao.exceptions import PIIVazadaError
from app.modules.anonimizacao.pseudonimizador import anonimizar as _anon
from app.modules.anonimizacao.recognizers import detectar_por_regex
from app.modules.consentimentos.exceptions import SemConsentimentoAtivo
from app.modules.llm import service
from app.modules.llm.exceptions import PacienteInexistente
from app.modules.llm.prompts import SYSTEM_INSTRUCAO, construir_mensagens, montar_bloco_dados
from app.modules.llm.schemas import GerarEvolucaoIn
from app.modules.llm.service import _parse_resposta

ENTIDADES = [("Pedro", "PERSON")]


class _FakeDB:
    """db.get(Model, id) -> objeto (paciente existe) ou None."""

    def __init__(self, paciente_existe=True):
        self._existe = paciente_existe

    def get(self, _model, _id):
        return object() if self._existe else None


def _user():
    return CurrentUser(id=uuid.uuid4(), tenant_id=uuid.uuid4(), papel="psicologa")


def _anon_real(entidades, texto):
    """Substitui `anonimizar_com_entidades` sem BD: pipeline real com entidades."""
    ac = AhoCorasick()
    for termo, cat in entidades:
        ac.adicionar(termo, cat)
    ac.finalizar()
    occ = [o for o in ac.buscar(texto) if respeita_fronteira(texto, o)] + detectar_por_regex(texto)
    return _anon(texto, occ)


def _patch_comum(monkeypatch, *, contexto, anon=_anon_real):
    monkeypatch.setattr(service, "entidades_do_paciente", lambda db, pid: ENTIDADES)
    monkeypatch.setattr(service, "buscar_contexto", lambda *a, **k: contexto)
    monkeypatch.setattr(service, "tem_consentimento_ativo", lambda db, pid: True)
    monkeypatch.setattr(service, "anonimizar_com_entidades", anon)


# --------------------------------------------------------------------------- #
# Prompt (separacao instrucao/dado §3.4)
# --------------------------------------------------------------------------- #
def test_bloco_de_dados_inclui_nota_e_historico():
    bloco = montar_bloco_dados("Nota de hoje.", ["trecho antigo A", "trecho antigo B"])
    assert "NOTA DO DIA" in bloco and "Nota de hoje." in bloco
    assert "HISTORICO" in bloco and "trecho antigo A" in bloco


def test_mensagens_separam_system_e_user():
    msgs = construir_mensagens("dados mascarados")
    assert msgs[0]["role"] == "system" and msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "dados mascarados"


def test_prompt_contem_palavra_json_minuscula():
    # response_format=json_object exige a substring "json" nas mensagens (#2).
    assert "json" in SYSTEM_INSTRUCAO


# --------------------------------------------------------------------------- #
# Fluxo feliz: nada de PII sai; resposta volta desanonimizada
# --------------------------------------------------------------------------- #
def test_gerar_rascunho_mascara_saida_e_desanonimiza_resposta(monkeypatch):
    enviado = {}

    def fake_gerar_json(mensagens):
        enviado["payload"] = mensagens[1]["content"]
        # O LLM "responde" usando os marcadores que recebeu.
        return '{"evolucao": "Hoje <PERSON_1> repetiu o padrao.", "destaques": ["<PERSON_1> tem gatilho sonoro"]}'

    _patch_comum(monkeypatch, contexto=["Pedro ja teve gatilho sonoro."])
    monkeypatch.setattr(service, "gerar_json", fake_gerar_json)

    out = service.gerar_rascunho(
        _FakeDB(), _user(), GerarEvolucaoIn(paciente_id=uuid.uuid4(), nota_do_dia="Hoje o Pedro teve crise.")
    )
    # O que saiu para a OpenAI nao tem o nome real, so marcador.
    assert "Pedro" not in enviado["payload"]
    assert "<PERSON_1>" in enviado["payload"]
    # A resposta volta desanonimizada para a psicologa.
    assert "Pedro" in out.evolucao and "<PERSON_1>" not in out.evolucao
    assert out.destaques and "Pedro" in out.destaques[0]
    assert out.chunks_contexto == 1


def test_marcador_alucinado_e_removido_da_saida(monkeypatch):
    # O LLM inventa <PERSON_9> (nao existe no mapa) -> nao pode vazar cru (#3).
    _patch_comum(monkeypatch, contexto=[])
    monkeypatch.setattr(
        service,
        "gerar_json",
        lambda msgs: '{"evolucao": "Nota sobre <PERSON_9> hoje.", "destaques": []}',
    )
    out = service.gerar_rascunho(
        _FakeDB(), _user(), GerarEvolucaoIn(paciente_id=uuid.uuid4(), nota_do_dia="Sem nomes.")
    )
    assert "<PERSON_9>" not in out.evolucao and "<PERSON" not in out.evolucao


def test_guard_rail_aborta_antes_da_openai(monkeypatch):
    chamou = {"llm": False}

    def nao_deveria(_msgs):
        chamou["llm"] = True
        return "{}"

    # anonimizacao "quebrada": devolve o texto sem mascarar -> PII vaza no payload.
    def anon_falha(_entidades, texto):
        from app.modules.anonimizacao.pseudonimizador import MapaPseudonimizacao

        return texto, MapaPseudonimizacao()

    _patch_comum(monkeypatch, contexto=["Pedro ja teve crise."], anon=anon_falha)
    monkeypatch.setattr(service, "gerar_json", nao_deveria)

    with pytest.raises(PIIVazadaError):
        service.gerar_rascunho(
            _FakeDB(), _user(), GerarEvolucaoIn(paciente_id=uuid.uuid4(), nota_do_dia="O Pedro veio.")
        )
    assert chamou["llm"] is False  # nada foi enviado a OpenAI


def test_gate_consentimento_bloqueia(monkeypatch):
    _patch_comum(monkeypatch, contexto=[])
    monkeypatch.setattr(service, "tem_consentimento_ativo", lambda db, pid: False)
    with pytest.raises(SemConsentimentoAtivo):
        service.gerar_rascunho(
            _FakeDB(), _user(), GerarEvolucaoIn(paciente_id=uuid.uuid4(), nota_do_dia="x")
        )


def test_paciente_inexistente(monkeypatch):
    _patch_comum(monkeypatch, contexto=[])
    with pytest.raises(PacienteInexistente):
        service.gerar_rascunho(
            _FakeDB(paciente_existe=False),
            _user(),
            GerarEvolucaoIn(paciente_id=uuid.uuid4(), nota_do_dia="x"),
        )


# --------------------------------------------------------------------------- #
# Parsing tolerante da resposta
# --------------------------------------------------------------------------- #
def test_parse_resposta_json_valido():
    ev, dest = _parse_resposta('{"evolucao": "texto", "destaques": ["a", "b"]}')
    assert ev == "texto" and dest == ["a", "b"]


def test_parse_resposta_json_invalido_cai_para_texto_cru():
    ev, dest = _parse_resposta("nao sou json")
    assert ev == "nao sou json" and dest == []


def test_parse_resposta_destaques_ausente():
    ev, dest = _parse_resposta('{"evolucao": "so evolucao"}')
    assert ev == "so evolucao" and dest == []


# --------------------------------------------------------------------------- #
# Consistencia de marcadores entre nota e historico (uma anonimizacao so)
# --------------------------------------------------------------------------- #
def test_mesmo_nome_recebe_mesmo_marcador_na_nota_e_no_historico():
    bloco = montar_bloco_dados("O Pedro teve crise.", ["Pedro ja tinha crises."])
    mascarado, _ = _anon_real(ENTIDADES, bloco)
    assert "Pedro" not in mascarado
    assert mascarado.count("<PERSON_1>") == 2  # mesmo marcador nos dois lugares


# --------------------------------------------------------------------------- #
# Cliente sem chave -> indisponivel
# --------------------------------------------------------------------------- #
def test_gerar_json_sem_chave_indisponivel():
    from app.modules.llm.client import gerar_json
    from app.modules.llm.exceptions import GeracaoIndisponivel

    with pytest.raises(GeracaoIndisponivel):
        gerar_json([{"role": "user", "content": "oi"}])
