"""Schemas Pydantic de evolucoes (Fase 5).

A resposta NAO expoe o embedding (vetor cru nao interessa ao cliente) nem o
texto anonimizado — so a nota crua legivel + metadados. `embeddings_pendentes`
sinaliza chunks que ainda nao foram vetorizados (OpenAI indisponivel no momento
da criacao) — um re-embed posterior resolve.

Regras de ouro: §3.2, §3.4
Fase do roadmap: Fase 5
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvolucaoCreate(BaseModel):
    paciente_id: uuid.UUID
    texto: str = Field(min_length=1)


class EvolucaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    paciente_id: uuid.UUID
    autor_usuario_id: uuid.UUID
    texto: str
    criado_em: datetime
    total_chunks: int
    embeddings_pendentes: int
