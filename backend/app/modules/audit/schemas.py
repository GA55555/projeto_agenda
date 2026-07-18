"""Schemas Pydantic do modulo de auditoria (append-only) — §2.2.

Somente saida: a auditoria e escrita internamente pelos servicos de dominio
(revogacao de consentimento, alteracao de guarda), nunca por payload da API.

Regras de ouro: §2.2
Fase do roadmap: Fase 3
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo_evento: str
    entidade: str
    entidade_id: uuid.UUID
    ator_usuario_id: uuid.UUID
    payload: dict[str, Any]
    criado_em: datetime
