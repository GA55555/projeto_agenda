"""Cliente OpenAI de chat — import lazy (§1.3), sem tools, retencao-zero (§3.4).

§3.4: a chamada NAO passa nenhuma tool/function (o LLM jamais toca o BD) e usa
`store=False` (a OpenAI nao retem o payload). Timeout curto: geracao sincrona
dentro do request, 2 workers (§1.3).

Regras de ouro: §3.4, §1.3
Fase do roadmap: Fase 6
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.modules.llm.exceptions import GeracaoIndisponivel


@lru_cache(maxsize=1)
def _client():
    """Cliente OpenAI, criado uma vez (import lazy §1.3). None se sem chave."""
    if not settings.openai_api_key:
        return None
    from openai import OpenAI  # import pesado DENTRO da funcao (§1.3)

    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_chat_timeout_seconds,  # maior que o de embeddings
        max_retries=1,
    )


def gerar_json(mensagens: list[dict[str, str]]) -> str:
    """Chama o chat e devolve o conteudo (string JSON). Levanta se indisponivel.

    Sem `tools` (§3.4 #1). `store=False` (retencao-zero §3.4 #6). O chamador ja
    garantiu que as mensagens contem apenas texto anonimizado (§2.3).
    """
    client = _client()
    if client is None:
        raise GeracaoIndisponivel("OPENAI_API_KEY ausente")
    try:
        resp = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=mensagens,
            temperature=settings.openai_chat_temperature,
            response_format={"type": "json_object"},
            store=False,
        )
    except Exception as exc:  # rede/quota/API/timeout
        raise GeracaoIndisponivel(str(exc)) from exc
    return resp.choices[0].message.content or ""
