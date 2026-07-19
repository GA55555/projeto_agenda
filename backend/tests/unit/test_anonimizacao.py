"""Testes do tunel opaco de pseudonimizacao (Fase 4, §2.3).

Cobrem o Definition of Done da Fase 4:
  - round-trip (anonimizar -> desanonimizar) preserva o texto;
  - nenhuma PII conhecida escapa (guard-rail);
  - o dicionario de equivalencia nao e persistido (so RAM);
  - fronteira de palavra, PII estruturada por regex e anti-backtracking.

Nao exigem BD: exercitam as camadas puras (Aho-Corasick + regex + pseudonimizador)
e mockam a fonte de entidades cadastradas. A camada NER (Presidio) e coberta por
um teste guardado por `importorskip` — roda so onde o extra `[nlp]` existe.

Regras de ouro: §2.3, §1.3
Fase do roadmap: Fase 4
"""
import time
import uuid

import pytest

from app.modules.anonimizacao import (
    MapaPseudonimizacao,
    desanonimizar_texto,
    verificar_sem_pii,
)
from app.modules.anonimizacao.automaton import AhoCorasick, respeita_fronteira
from app.modules.anonimizacao.guardrail import encontrar_pii_conhecida
from app.modules.anonimizacao.exceptions import PIIVazadaError
from app.modules.anonimizacao.pseudonimizador import anonimizar, desanonimizar
from app.modules.anonimizacao.recognizers import detectar_por_regex
from app.modules.anonimizacao import service


# --------------------------------------------------------------------------- #
# Aho-Corasick
# --------------------------------------------------------------------------- #
def test_automaton_casa_multiplos_padroes_em_uma_passagem():
    ac = AhoCorasick()
    ac.adicionar("Pedro", "PERSON")
    ac.adicionar("Belo Horizonte", "LOCATION")
    ac.finalizar()
    texto = "O Pedro mora em Belo Horizonte."
    encontrados = {(texto[o.inicio : o.fim], o.categoria) for o in ac.buscar(texto)}
    assert ("Pedro", "PERSON") in encontrados
    assert ("Belo Horizonte", "LOCATION") in encontrados


def test_automaton_case_insensitive_preserva_offsets():
    ac = AhoCorasick()
    ac.adicionar("pedro", "PERSON")
    ac.finalizar()
    texto = "Falei com PEDRO hoje."
    ocs = ac.buscar(texto)
    assert len(ocs) == 1
    assert texto[ocs[0].inicio : ocs[0].fim] == "PEDRO"


def test_automaton_ligacao_de_falha_sufixos():
    # "he" e sufixo dentro de "she" — as ligacoes de falha devem casar ambos.
    ac = AhoCorasick()
    ac.adicionar("he", "X")
    ac.adicionar("she", "Y")
    ac.finalizar()
    cats = sorted(o.categoria for o in ac.buscar("she"))
    assert cats == ["X", "Y"]


def test_offset_alinhado_com_char_que_cresce_no_lower():
    # 'İ' (U+0130).lower() == 'i̇' (2 code points). O _fold preserva o
    # comprimento, entao os offsets seguintes NAO deslocam e a PII e mascarada
    # no lugar certo (regressao do fix #1 do code-review, §2.3).
    ac = AhoCorasick()
    ac.adicionar("Pedro", "PERSON")
    ac.finalizar()
    texto = "İ paciente Pedro chegou"  # char que cresce ANTES da PII
    ocs = [o for o in ac.buscar(texto) if respeita_fronteira(texto, o)]
    assert len(ocs) == 1
    assert texto[ocs[0].inicio : ocs[0].fim] == "Pedro"


def test_fronteira_de_palavra_evita_pedro_em_pedrosa():
    ac = AhoCorasick()
    ac.adicionar("Pedro", "PERSON")
    ac.finalizar()
    texto = "A familia Pedrosa chegou."
    validas = [o for o in ac.buscar(texto) if respeita_fronteira(texto, o)]
    assert validas == []  # "Pedro" dentro de "Pedrosa" nao conta


# --------------------------------------------------------------------------- #
# Regex (PII estruturada)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "texto,categoria",
    [
        ("CPF 123.456.789-09 do responsavel", "CPF"),
        ("ligar (31) 98888-7777", "PHONE"),
        ("email mae@exemplo.com.br", "EMAIL"),
        ("CEP 30110-010 centro", "CEP"),
    ],
)
def test_regex_detecta_pii_estruturada(texto, categoria):
    cats = {o.categoria for o in detectar_por_regex(texto)}
    assert categoria in cats


def test_regex_anti_backtracking_termina_rapido():
    # Entrada patologica: muitos digitos e simbolos. Padroes ancorados =>
    # tempo linear. Deve terminar bem abaixo de 1s (§2.3).
    texto = ("1" * 5000) + "@" + ("a" * 5000) + " " + ("9 " * 5000)
    inicio = time.perf_counter()
    detectar_por_regex(texto)
    assert time.perf_counter() - inicio < 1.0


# --------------------------------------------------------------------------- #
# Pseudonimizador: round-trip, numeracao, idempotencia
# --------------------------------------------------------------------------- #
def _detectar(texto, entidades):
    ac = AhoCorasick()
    for termo, cat in entidades:
        ac.adicionar(termo, cat)
    ac.finalizar()
    conhecidos = [o for o in ac.buscar(texto) if respeita_fronteira(texto, o)]
    return conhecidos + detectar_por_regex(texto)


def test_round_trip_preserva_texto():
    texto = "O Pedro apresentou crises na escola. CPF 123.456.789-09."
    entidades = [("Pedro", "PERSON")]
    mascarado, mapa = anonimizar(texto, _detectar(texto, entidades))
    assert "Pedro" not in mascarado
    assert "123.456.789-09" not in mascarado
    assert "<PERSON_1>" in mascarado
    assert desanonimizar(mascarado, mapa) == texto


def test_marcadores_sequenciais_e_idempotentes():
    texto = "Pedro e Ana. Pedro de novo, e Ana tambem."
    entidades = [("Pedro", "PERSON"), ("Ana", "PERSON")]
    mascarado, mapa = anonimizar(texto, _detectar(texto, entidades))
    # Mesma entidade -> mesmo marcador; numeracao por 1a aparicao.
    assert mascarado.count("<PERSON_1>") == 2  # Pedro (2x)
    assert mascarado.count("<PERSON_2>") == 2  # Ana (2x)
    assert mapa.original_de("<PERSON_1>") == "Pedro"
    assert mapa.original_de("<PERSON_2>") == "Ana"
    assert desanonimizar(mascarado, mapa) == texto


def test_desempate_categoria_cpf_vence_telefone_em_11_digitos():
    # 11 digitos "crus" casam CPF e telefone (mesmo span). O desempate
    # deterministico escolhe CPF; o importante e que NADA vaza (regressao #5).
    texto = "documento 12345678909 do responsavel"
    mascarado, _ = anonimizar(texto, detectar_por_regex(texto))
    assert "12345678909" not in mascarado
    assert "<CPF_1>" in mascarado


def test_sobreposicao_mais_longo_vence():
    texto = "escola de Belo Horizonte"
    entidades = [("Belo", "LOCATION"), ("Belo Horizonte", "LOCATION")]
    mascarado, _ = anonimizar(texto, _detectar(texto, entidades))
    assert "Belo Horizonte" not in mascarado
    assert "Horizonte" not in mascarado  # o span longo cobriu tudo


# --------------------------------------------------------------------------- #
# Dicionario volatil: NAO persiste (§2.3)
# --------------------------------------------------------------------------- #
def test_mapa_nao_e_model_e_repr_nao_vaza_pii():
    from app.db.base import Base

    _, mapa = anonimizar("Pedro foi a escola.", [])
    assert not isinstance(mapa, Base)  # nao e entidade SQLAlchemy (nao persiste)
    mapa.marcador_para("PERSON", "Pedro")
    assert "Pedro" not in repr(mapa)  # repr esconde valores (nao vaza em logs)


def test_modulo_nao_declara_tabela_nem_router():
    # A NAO-persistencia da Fase 4 e estrutural: sem models.py / router.py.
    import importlib

    for nome in ("models", "router"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(f"app.modules.anonimizacao.{nome}")


# --------------------------------------------------------------------------- #
# Guard-rail de saida (§2.3)
# --------------------------------------------------------------------------- #
def test_guardrail_barra_pii_que_escapou():
    termos = [("Pedro", "PERSON")]
    with pytest.raises(PIIVazadaError) as exc:
        verificar_sem_pii("resumo: Pedro melhorou", termos)
    assert "Pedro" in exc.value.termos


def test_guardrail_aprova_texto_mascarado():
    termos = [("Pedro", "PERSON")]
    verificar_sem_pii("resumo: <PERSON_1> melhorou", termos)  # nao levanta


def test_guardrail_respeita_fronteira():
    termos = [("Ana", "PERSON")]
    # "Ana" dentro de "Fernanda" nao deve ser tratado como vazamento.
    assert encontrar_pii_conhecida("A Fernanda chegou", termos) == []


# --------------------------------------------------------------------------- #
# Orquestracao do service (mockando a fonte de entidades e o NER)
# --------------------------------------------------------------------------- #
def test_service_orquestra_camadas(monkeypatch):
    entidades = [("Pedro", "PERSON"), ("Clinica Alfa", "ORG")]
    monkeypatch.setattr(service, "coletar_entidades", lambda db, pid: entidades)
    monkeypatch.setattr(service, "detectar_por_ner", lambda texto: [])
    texto = "Pedro foi atendido na Clinica Alfa. Tel (31) 98888-7777."
    mascarado, mapa = service.anonimizar_texto(object(), uuid.uuid4(), texto)
    assert "Pedro" not in mascarado
    assert "Clinica Alfa" not in mascarado
    assert "98888-7777" not in mascarado
    assert service.desanonimizar_texto(mascarado, mapa) == texto
    # Guard-rail confirma que nenhuma PII conhecida sobrou.
    verificar_sem_pii(mascarado, entidades)


# --------------------------------------------------------------------------- #
# Camada NER (so roda com o extra [nlp] instalado)
# --------------------------------------------------------------------------- #
def test_ner_detecta_pessoa_nao_cadastrada():
    pytest.importorskip("presidio_analyzer")
    from app.modules.anonimizacao.nlp import detectar_por_ner, ner_disponivel

    if not ner_disponivel():
        pytest.skip("modelo spaCy pt nao instalado")
    ocs = detectar_por_ner("O paciente brincou com o Lucas na quadra.")
    assert any(o.categoria == "PERSON" for o in ocs)
