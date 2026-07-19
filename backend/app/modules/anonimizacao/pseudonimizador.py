"""Nucleo do tunel opaco: dicionario volatil + Anonymizer/Deanonymizer (§2.3).

Fluxo (§2.3):
  1. Entidades reais -> marcadores sequenciais (`<PERSON_1>`, `<LOCATION_1>`...).
  2. Tabela de equivalencia `<PERSON_1> -> "Pedro"` mantida APENAS em memoria
     volatil (`MapaPseudonimizacao`), atrelada a requisicao. NUNCA persistida.
  3. Deanonymizer restaura os marcadores antes de exibir a resposta.

Fidelidade do round-trip: o marcador e reutilizado somente quando o trecho
casado e IDENTICO (mesma categoria + mesma substring exata). Assim a
desanonimizacao restaura byte-a-byte o texto original — sem heuristica de
casing que possa corromper o retorno.

Regras de ouro: §2.3
Fase do roadmap: Fase 4
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.anonimizacao.automaton import Ocorrencia


class MapaPseudonimizacao:
    """Dicionario de equivalencia marcador<->original — SO em RAM (§2.3).

    Vive no escopo de uma unica requisicao e e descartado ao seu fim. Nao e um
    model SQLAlchemy, nao tem serializador e o `__repr__` esconde os valores
    para nao vazar PII em stack traces/logs. Se a requisicao morre, o mapa morre.
    """

    def __init__(self) -> None:
        self._para_original: dict[str, str] = {}
        self._para_marcador: dict[tuple[str, str], str] = {}
        self._contadores: dict[str, int] = {}

    def marcador_para(self, categoria: str, valor: str) -> str:
        """Marcador estavel para (categoria, valor). Idempotente por trecho exato."""
        chave = (categoria, valor)
        existente = self._para_marcador.get(chave)
        if existente is not None:
            return existente
        proximo = self._contadores.get(categoria, 0) + 1
        self._contadores[categoria] = proximo
        marcador = f"<{categoria}_{proximo}>"
        self._para_marcador[chave] = marcador
        self._para_original[marcador] = valor
        return marcador

    def original_de(self, marcador: str) -> str | None:
        return self._para_original.get(marcador)

    @property
    def entradas(self) -> dict[str, str]:
        """Copia marcador->original (para inspecao/testes; nunca persistir)."""
        return dict(self._para_original)

    def __len__(self) -> int:
        return len(self._para_original)

    def __repr__(self) -> str:  # nao vaza PII em logs/tracebacks (§2.3)
        return f"<MapaPseudonimizacao entradas={len(self._para_original)}>"


# Desempate DETERMINISTICO quando dois spans tem mesmo tamanho e mesma posicao
# (ex.: 11 digitos "crus" casam CPF e telefone ao mesmo tempo). Menor numero
# vence. Preferimos a categoria mais identificante/estruturada — nao ha risco de
# vazamento, pois o trecho e mascarado de qualquer forma (§2.3, risco-zero); a
# ordem so torna o ROTULO do marcador estavel e previsivel.
_PRIORIDADE_CATEGORIA = {
    "EMAIL": 0,
    "CPF": 1,
    "CEP": 2,
    "PHONE": 3,
    "PERSON": 4,
    "ORG": 5,
    "ADDRESS": 6,
    "LOCATION": 7,
}


@dataclass
class _SpanEscolhido:
    inicio: int
    fim: int
    categoria: str
    texto: str = field(default="")


def _resolver_sobreposicoes(texto: str, ocorrencias: list[Ocorrencia]) -> list[_SpanEscolhido]:
    """Seleciona spans sem sobreposicao: MAIS LONGO vence, depois mais a esquerda."""
    # Ordena por comprimento desc, inicio asc, prioridade de categoria asc ->
    # a gulosa escolhe o maior; empates resolvem de forma estavel e documentada.
    ordenadas = sorted(
        ocorrencias,
        key=lambda o: (-o.comprimento, o.inicio, _PRIORIDADE_CATEGORIA.get(o.categoria, 99)),
    )
    ocupado = [False] * len(texto)
    escolhidos: list[_SpanEscolhido] = []
    for oc in ordenadas:
        if any(ocupado[oc.inicio : oc.fim]):
            continue
        for i in range(oc.inicio, oc.fim):
            ocupado[i] = True
        escolhidos.append(
            _SpanEscolhido(oc.inicio, oc.fim, oc.categoria, texto[oc.inicio : oc.fim])
        )
    # Ordem de leitura (esquerda->direita) para numeracao sequencial estavel.
    escolhidos.sort(key=lambda s: s.inicio)
    return escolhidos


def anonimizar(texto: str, ocorrencias: list[Ocorrencia]) -> tuple[str, MapaPseudonimizacao]:
    """Substitui as PII detectadas por marcadores. Devolve (texto_mascarado, mapa)."""
    mapa = MapaPseudonimizacao()
    spans = _resolver_sobreposicoes(texto, ocorrencias)
    if not spans:
        return texto, mapa
    partes: list[str] = []
    cursor = 0
    for s in spans:
        partes.append(texto[cursor : s.inicio])
        partes.append(mapa.marcador_para(s.categoria, s.texto))
        cursor = s.fim
    partes.append(texto[cursor:])
    return "".join(partes), mapa


def desanonimizar(texto: str, mapa: MapaPseudonimizacao) -> str:
    """Restaura os marcadores com o dicionario volatil (Deanonymizer, §2.3)."""
    resultado = texto
    entradas = mapa.entradas  # captura uma vez (a property copia o dict)
    # Marcadores mais longos primeiro (o delimitador `>` ja evita colisao de
    # prefixo entre `<PERSON_1>` e `<PERSON_11>`, mas ordenar e defensivo).
    for marcador in sorted(entradas, key=len, reverse=True):
        resultado = resultado.replace(marcador, entradas[marcador])
    return resultado
