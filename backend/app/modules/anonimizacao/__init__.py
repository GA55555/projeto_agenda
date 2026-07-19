"""Tunel opaco de pseudonimizacao (Aho-Corasick + regex + NER lazy, §2.3).

API publica do modulo (biblioteca interna, sem rota — consumida pela Fase 6):
  - `anonimizar_texto(db, paciente_id, texto) -> (mascarado, mapa_volatil)`
  - `desanonimizar_texto(texto, mapa) -> texto original`
  - `entidades_do_paciente(db, paciente_id)` — termos conhecidos p/ o guard-rail
  - `verificar_sem_pii(payload, termos)` — aborta se PII conhecida escapar
  - `MapaPseudonimizacao` — dicionario de equivalencia SO em RAM (nunca persiste)

Regras de ouro: §2.3, §1.3
Fase do roadmap: Fase 4
"""
from app.modules.anonimizacao.guardrail import verificar_sem_pii
from app.modules.anonimizacao.pseudonimizador import MapaPseudonimizacao
from app.modules.anonimizacao.service import (
    anonimizar_texto,
    desanonimizar_texto,
    entidades_do_paciente,
)

__all__ = [
    "anonimizar_texto",
    "desanonimizar_texto",
    "entidades_do_paciente",
    "verificar_sem_pii",
    "MapaPseudonimizacao",
]
