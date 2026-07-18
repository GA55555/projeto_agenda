"""Schemas Pydantic do modulo de tenants.

Regras de ouro: §2.1
Fase do roadmap: Fase 2
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    slug: str
    ativo: bool
    criado_em: datetime
