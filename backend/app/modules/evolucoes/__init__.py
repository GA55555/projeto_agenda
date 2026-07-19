"""Evolucoes/prontuarios clinicos + embeddings longitudinais (RAG, §3.1-§3.4).

API publica consumida pela Fase 6 (LLM):
  - `criar_evolucao` / `listar_por_paciente` / `obter`
  - `buscar_contexto(db, tenant_id, paciente_id, texto_novo, entidades, k)` — RAG

Regras de ouro: §3.1, §3.2, §3.3, §3.4
Fase do roadmap: Fase 5
"""
from app.modules.evolucoes.service import (
    buscar_contexto,
    criar_evolucao,
    listar_por_paciente,
    obter,
)

__all__ = ["criar_evolucao", "listar_por_paciente", "obter", "buscar_contexto"]
