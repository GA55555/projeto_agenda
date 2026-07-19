"""Orquestracao do tunel opaco de pseudonimizacao (§2.3).

Combina as tres camadas de deteccao numa unica passagem de mascaramento:
  1. Termos CADASTRADOS (Aho-Corasick, §2.3) — nome/CPF/telefone/e-mail/endereco
     do paciente e responsaveis + nome da clinica, com fronteira de palavra.
  2. Regex ANCORADO — CPF/telefone/e-mail/CEP digitados no texto livre.
  3. NER (Presidio, lazy §1.3) — pessoas/locais nao cadastrados (reforco).

Nenhum acesso cross-tenant: `coletar_entidades` roda sob a sessao com RLS (§2.1).

Dicionario volatil (§2.3): o `MapaPseudonimizacao` devolvido vive so em RAM, no
escopo da requisicao do chamador. Nao ha model, tabela nem migration neste
modulo — a NAO-persistencia e a garantia da regra de ouro. Se a requisicao
morre, o mapa morre com ela.

Regras de ouro: §2.3, §2.1, §1.3
Fase do roadmap: Fase 4
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.modules.anonimizacao.automaton import AhoCorasick, Ocorrencia, respeita_fronteira
from app.modules.anonimizacao.nlp import detectar_por_ner
from app.modules.anonimizacao.pseudonimizador import (
    MapaPseudonimizacao,
    anonimizar,
    desanonimizar,
)
from app.modules.anonimizacao.recognizers import detectar_por_regex
from app.modules.anonimizacao.sources import coletar_entidades


def _detectar_cadastrados(texto: str, entidades: list[tuple[str, str]]) -> list[Ocorrencia]:
    """Ocorrencias dos termos cadastrados, ja filtradas por fronteira de palavra."""
    if not entidades:
        return []
    automaton = AhoCorasick()
    for termo, categoria in entidades:
        automaton.adicionar(termo, categoria)
    automaton.finalizar()
    return [oc for oc in automaton.buscar(texto) if respeita_fronteira(texto, oc)]


def anonimizar_texto(
    db: Session, paciente_id: uuid.UUID, texto: str
) -> tuple[str, MapaPseudonimizacao]:
    """Mascara todas as PII do texto. Devolve (texto_mascarado, mapa volatil).

    `db` deve carregar o contexto de tenant (RLS ativo) — as entidades cadastradas
    sao lidas sob isolamento do motor (§2.1).
    """
    return anonimizar_com_entidades(coletar_entidades(db, paciente_id), texto)


def anonimizar_com_entidades(
    entidades: list[tuple[str, str]], texto: str
) -> tuple[str, MapaPseudonimizacao]:
    """Como `anonimizar_texto`, mas com entidades JA coletadas (sem tocar o BD).

    Evita re-consultar `coletar_entidades` quando o chamador vai anonimizar
    varios textos do mesmo paciente (ex.: chunks na Fase 5, bloco de prompt na
    Fase 6) — coleta uma vez e reusa.
    """
    ocorrencias: list[Ocorrencia] = []
    ocorrencias.extend(_detectar_cadastrados(texto, entidades))
    ocorrencias.extend(detectar_por_regex(texto))
    ocorrencias.extend(detectar_por_ner(texto))
    return anonimizar(texto, ocorrencias)


def desanonimizar_texto(texto: str, mapa: MapaPseudonimizacao) -> str:
    """Restaura os marcadores no texto de resposta com o dicionario volatil (§2.3)."""
    return desanonimizar(texto, mapa)


def entidades_do_paciente(db: Session, paciente_id: uuid.UUID) -> list[tuple[str, str]]:
    """Termos conhecidos (para o guard-rail de saida da Fase 6)."""
    return coletar_entidades(db, paciente_id)
