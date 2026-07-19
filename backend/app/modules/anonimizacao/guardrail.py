"""Guard-rail de saida: barra PII conhecida antes de sair para o LLM (§2.3).

Ultima verificacao defensiva do tunel opaco. Dada a lista de termos conhecidos
do paciente e o payload que SERIA enviado a OpenAI, aborta (levanta
`PIIVazadaError`) se qualquer termo escapou o mascaramento. A Fase 6 chama isto
imediatamente antes da requisicao externa — nenhum byte de PII conhecida deixa
o processo.

A deteccao reusa o Aho-Corasick + fronteira de palavra (mesma logica do
mascaramento), garantindo simetria: o que seria mascarado e o que e barrado sao
o mesmo conjunto.

Regras de ouro: §2.3
Fase do roadmap: Fase 4
"""
from __future__ import annotations

from app.modules.anonimizacao.automaton import AhoCorasick, respeita_fronteira
from app.modules.anonimizacao.exceptions import PIIVazadaError


def encontrar_pii_conhecida(payload: str, termos: list[tuple[str, str]]) -> list[str]:
    """Trechos de PII conhecida presentes no payload (fronteira de palavra)."""
    if not termos:
        return []
    automaton = AhoCorasick()
    for termo, categoria in termos:
        automaton.adicionar(termo, categoria)
    automaton.finalizar()
    vazados: list[str] = []
    vistos: set[str] = set()
    for oc in automaton.buscar(payload):
        if not respeita_fronteira(payload, oc):
            continue
        trecho = payload[oc.inicio : oc.fim]
        if trecho not in vistos:
            vistos.add(trecho)
            vazados.append(trecho)
    return vazados


def verificar_sem_pii(payload: str, termos: list[tuple[str, str]]) -> None:
    """Aborta (PIIVazadaError) se alguma PII conhecida escapou no payload (§2.3)."""
    vazados = encontrar_pii_conhecida(payload, termos)
    if vazados:
        raise PIIVazadaError(vazados)
