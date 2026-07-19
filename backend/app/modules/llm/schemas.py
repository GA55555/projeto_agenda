"""Schemas Pydantic da geracao de evolucao (Fase 6).

Entrada: paciente + nota do dia (crua — sera anonimizada no service, §2.3).
Saida: rascunho DESANONIMIZADO (legivel p/ a psicologa aprovar na Fase 7).
Nada e persistido nesta fase (stateless).

Regras de ouro: §2.3, §3.4
Fase do roadmap: Fase 6
"""
import uuid

from pydantic import BaseModel, Field


class GerarEvolucaoIn(BaseModel):
    paciente_id: uuid.UUID
    nota_do_dia: str = Field(min_length=1)


class RascunhoOut(BaseModel):
    # Rascunho para revisao — NAO e evolucao gravada nem laudo final.
    evolucao: str
    destaques: list[str]
    # Quantos trechos do historico (RAG) alimentaram o prompt (transparencia).
    chunks_contexto: int
