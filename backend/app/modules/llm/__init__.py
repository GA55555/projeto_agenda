"""Integracao LLM (OpenAI): tunel completo anonimiza -> gera -> desanonimiza.

API publica:
  - `gerar_rascunho(db, user, dados) -> RascunhoOut` — rascunho de evolucao +
    destaques longitudinais, a partir da nota do dia + historico (RAG), tudo
    anonimizado (§2.3/§3.4). Stateless: nao persiste.

Regras de ouro: §2.3, §3.3, §3.4
Fase do roadmap: Fase 6
"""
from app.modules.llm.service import gerar_rascunho

__all__ = ["gerar_rascunho"]
