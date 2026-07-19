"""Geracao de embeddings via OpenAI (§3.1/§3.4/§1.3).

O cliente `openai` e importado LAZY (§1.3), so quando um embedding e realmente
gerado. O texto que chega aqui JA vem anonimizado do service (§3.4) — esta
camada nao conhece PII, so recebe texto mascarado/canonicalizado.

Canonicalizacao de marcadores: `<PERSON_1>`/`<PERSON_2>` -> `<PERSON>`. Os
numeros sequenciais sao ruido para o vetor (identidade nao importa para a
semantica clinica); canonicalizar melhora a comparabilidade entre chunks/notas
sem reintroduzir PII.

Regras de ouro: §3.1, §3.4, §1.3
Fase do roadmap: Fase 5
"""
from __future__ import annotations

import re
from functools import lru_cache

from app.core.config import settings
from app.modules.evolucoes.exceptions import EmbeddingIndisponivel

_MARCADOR_NUMERADO = re.compile(r"<([A-Z]+)_\d+>")


def canonicalizar_marcadores(texto: str) -> str:
    """`<CAT_n>` -> `<CAT>` (remove a numeracao, ruido para o embedding)."""
    return _MARCADOR_NUMERADO.sub(r"<\1>", texto)


@lru_cache(maxsize=1)
def _client():
    """Cliente OpenAI, criado uma vez (import lazy §1.3). None se sem chave."""
    if not settings.openai_api_key:
        return None
    from openai import OpenAI  # import pesado DENTRO da funcao (§1.3)

    # timeout curto + poucos retries: sincrono dentro do request, 2 workers (§1.3).
    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
        max_retries=1,
    )


def gerar_embedding(texto_anonimizado: str) -> list[float]:
    """Vetor 1536-d do texto JA anonimizado (§3.4). Levanta se indisponivel.

    O chamador (service) e responsavel por garantir que `texto_anonimizado`
    passou pelo tunel §2.3 e pelo guard-rail antes de chegar aqui.
    """
    client = _client()
    if client is None:
        raise EmbeddingIndisponivel("OPENAI_API_KEY ausente")
    try:
        resp = client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texto_anonimizado,
        )
    except Exception as exc:  # falha de rede/quota/API -> nota persiste sem vetor
        raise EmbeddingIndisponivel(str(exc)) from exc
    return resp.data[0].embedding
