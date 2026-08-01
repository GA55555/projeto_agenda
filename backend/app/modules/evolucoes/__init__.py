"""Evolucoes/prontuarios clinicos + embeddings longitudinais (RAG, §3.1-§3.4).

API publica consumida pela Fase 6 (LLM):
  - `criar_evolucao` / `listar_por_paciente` / `obter`
  - `buscar_contexto(db, tenant_id, paciente_id, texto_novo, entidades, k)` — RAG

Regras de ouro: §3.1, §3.2, §3.3, §3.4
Fase do roadmap: Fase 5
"""
from collections.abc import Callable
from importlib import import_module
from typing import Any

__all__ = ["criar_evolucao", "listar_por_paciente", "obter", "buscar_contexto"]


def __getattr__(name: str) -> Callable[..., Any]:
    """Mantém a API pública sem importar service durante o registro dos models.

    `n8n.service` precisa importar `Evolucao`; por sua vez, `evolucoes.service`
    enfileira no n8n. Carregar o service aqui de forma eager criava um ciclo.
    """
    if name not in __all__:
        raise AttributeError(name)
    service = import_module("app.modules.evolucoes.service")
    return getattr(service, name)
