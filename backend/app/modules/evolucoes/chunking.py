"""Segmentacao de prontuarios em blocos logicos (§3.3).

Prontuarios longos sao particionados ANTES de vetorizados: cada bloco vira um
chunk com seu proprio embedding, para que a filtragem hibrida (§3.2) recupere
so os trechos relevantes daquele paciente, sem ruido nem desperdicio de tokens.

Estrategia: primeiro por paragrafos (linhas em branco = fronteira logica);
paragrafos maiores que `max_chars` sao subdivididos por frases, com uma pequena
sobreposicao (`overlap_chars`) entre janelas para nao cortar contexto no meio.
Funcao pura (sem I/O) — facil de testar.

Regras de ouro: §3.3
Fase do roadmap: Fase 5
"""
from __future__ import annotations

import re

# Limiares conservadores: notas clinicas sao curtas; blocos pequenos melhoram a
# precisao da recuperacao. Nao ha custo de RAM (sem indice vetorial, §3.1).
MAX_CHARS = 1000
OVERLAP_CHARS = 100

_QUEBRA_PARAGRAFO = re.compile(r"\n\s*\n")
_FIM_DE_FRASE = re.compile(r"(?<=[.!?])\s+")


def _subdividir_longo(paragrafo: str, max_chars: int, overlap: int) -> list[str]:
    """Divide um paragrafo longo por frases, respeitando `max_chars` + overlap."""
    frases = _FIM_DE_FRASE.split(paragrafo)
    blocos: list[str] = []
    atual = ""
    for frase in frases:
        if not frase:
            continue
        candidato = f"{atual} {frase}".strip() if atual else frase
        if len(candidato) <= max_chars:
            atual = candidato
            continue
        if atual:
            blocos.append(atual)
            # Semente do proximo bloco com a cauda do anterior (overlap de contexto).
            cauda = atual[-overlap:] if overlap else ""
            atual = f"{cauda} {frase}".strip() if cauda else frase
        else:
            # Frase unica maior que o limite: fatia dura por tamanho.
            for i in range(0, len(frase), max_chars):
                blocos.append(frase[i : i + max_chars])
            atual = ""
    if atual:
        blocos.append(atual)
    return blocos


def dividir_em_chunks(
    texto: str, *, max_chars: int = MAX_CHARS, overlap_chars: int = OVERLAP_CHARS
) -> list[str]:
    """Particiona o texto em blocos logicos <= max_chars (§3.3)."""
    chunks: list[str] = []
    for paragrafo in _QUEBRA_PARAGRAFO.split(texto.strip()):
        p = paragrafo.strip()
        if not p:
            continue
        if len(p) <= max_chars:
            chunks.append(p)
        else:
            chunks.extend(_subdividir_longo(p, max_chars, overlap_chars))
    return chunks
