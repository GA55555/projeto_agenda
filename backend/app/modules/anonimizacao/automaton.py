"""Aho-Corasick puro (stdlib) — deteccao de multiplas strings em uma passagem.

§2.3 exige correspondencia de multiplas strings SEM o *catastrophic backtracking*
do Regex tradicional. O automaton (trie + ligacoes de falha) resolve todas as
ocorrencias em O(n + m + z) — n = tamanho do texto, m = soma dos padroes,
z = numero de ocorrencias — numa unica varredura linear.

Implementacao propria em Python puro (sem dependencia compilada): os padroes
conhecidos por paciente sao poucos (dezenas) e as notas clinicas sao curtas,
entao o footprint fica minimo, alinhado ao §1.3 (nao carregar libs pesadas).

O casamento e case-insensitive via `_fold`, que rebaixa cada caractere
PRESERVANDO O COMPRIMENTO (1 char -> 1 char). Isso e critico: como os offsets
retornados indexam o texto ORIGINAL, qualquer desalinhamento deslocaria o
mascaramento e poderia deixar PII vazar (§2.3). `str.lower()` puro NAO serve
porque alguns caracteres crescem (ex.: 'İ'.lower() == 'i̇', 2 code points) —
esses sao mantidos como estao, sacrificando o casamento caseless raro em favor
da integridade dos offsets.

Regras de ouro: §2.3, §1.3
Fase do roadmap: Fase 4
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


def _fold(s: str) -> str:
    """Rebaixa caixa preservando o comprimento (1 char -> 1 char).

    Se `ch.lower()` produzir != 1 caractere, mantem o original — assim
    `len(_fold(s)) == len(s)` SEMPRE e os offsets do `buscar` alinham com o
    texto original. Padroes e texto passam pela MESMA transformacao, entao o
    casamento permanece coerente.
    """
    out = []
    for ch in s:
        low = ch.lower()
        out.append(low if len(low) == 1 else ch)
    return "".join(out)


@dataclass
class _No:
    """No da trie do automaton."""

    filhos: dict[str, "_No"] = field(default_factory=dict)
    falha: "_No | None" = None
    # Comprimentos dos padroes que terminam neste no (via ligacoes de falha),
    # com a carga (categoria) associada a cada padrao.
    saidas: list[tuple[int, str]] = field(default_factory=list)


@dataclass(frozen=True)
class Ocorrencia:
    """Uma ocorrencia de padrao no texto: [inicio, fim) e a categoria."""

    inicio: int
    fim: int
    categoria: str

    @property
    def comprimento(self) -> int:
        return self.fim - self.inicio


class AhoCorasick:
    """Automaton imutavel apos `finalizar()`. Construir uma vez, buscar N vezes."""

    def __init__(self) -> None:
        self._raiz = _No()
        self._finalizado = False

    def adicionar(self, padrao: str, categoria: str) -> None:
        """Registra um padrao (case-insensitive) com sua categoria."""
        if self._finalizado:
            raise RuntimeError("automaton ja finalizado; nao aceita novos padroes")
        padrao_norm = _fold(padrao)
        if not padrao_norm:
            return
        no = self._raiz
        for ch in padrao_norm:
            no = no.filhos.setdefault(ch, _No())
        # Guarda comprimento pelo padrao normalizado (== ao original em latino).
        no.saidas.append((len(padrao_norm), categoria))

    def finalizar(self) -> "AhoCorasick":
        """Constroi as ligacoes de falha (BFS). Idempotente."""
        if self._finalizado:
            return self
        fila: deque[_No] = deque()
        for filho in self._raiz.filhos.values():
            filho.falha = self._raiz
            fila.append(filho)
        while fila:
            atual = fila.popleft()
            for ch, filho in atual.filhos.items():
                fila.append(filho)
                falha = atual.falha
                while falha is not None and ch not in falha.filhos:
                    falha = falha.falha
                filho.falha = falha.filhos[ch] if falha and ch in falha.filhos else self._raiz
                # Herda as saidas do no de falha (padroes sufixos que tambem casam).
                filho.saidas.extend(filho.falha.saidas)
        self._finalizado = True
        return self

    def buscar(self, texto: str) -> list[Ocorrencia]:
        """Devolve todas as ocorrencias no texto (uma passagem linear)."""
        if not self._finalizado:
            raise RuntimeError("chame finalizar() antes de buscar")
        alvo = _fold(texto)  # mesmo comprimento do original -> offsets alinham
        ocorrencias: list[Ocorrencia] = []
        no = self._raiz
        for i, ch in enumerate(alvo):
            while no is not self._raiz and ch not in no.filhos:
                no = no.falha or self._raiz
            no = no.filhos.get(ch, self._raiz)
            for comprimento, categoria in no.saidas:
                fim = i + 1
                ocorrencias.append(Ocorrencia(fim - comprimento, fim, categoria))
        return ocorrencias


def respeita_fronteira(texto: str, oc: Ocorrencia) -> bool:
    """True se a ocorrencia esta em fronteira de palavra.

    Evita mascarar "Pedro" dentro de "Pedrosa": exige que os vizinhos imediatos
    do trecho nao sejam alfanumericos (acentos contam como alnum via `isalnum`).
    """
    antes_ok = oc.inicio == 0 or not texto[oc.inicio - 1].isalnum()
    depois_ok = oc.fim == len(texto) or not texto[oc.fim].isalnum()
    return antes_ok and depois_ok
