"""Schemas Pydantic do modulo de consentimentos (TCLE) — §2.2.

`ConsentimentoCreate` e reutilizado pela criacao de paciente (o TCLE e
obrigatorio no mesmo ato — invariante do DoD da Fase 3).

Regras de ouro: §2.2
Fase do roadmap: Fase 3
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConsentimentoCreate(BaseModel):
    """TCLE especifico (sem clausulas genericas, §2.2). `paciente_id` nao entra
    aqui: no fluxo de criacao de paciente ele e o paciente sendo criado."""

    responsavel_id: uuid.UUID
    finalidade_clinica: str = Field(min_length=1)
    limitacoes_acesso: str = Field(min_length=1)
    termo_versao: str = Field(min_length=1, max_length=50)
    termo_texto: str = Field(min_length=1)


class RevogacaoIn(BaseModel):
    motivo: str | None = None


class ConsentimentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    paciente_id: uuid.UUID
    responsavel_id: uuid.UUID
    finalidade_clinica: str
    limitacoes_acesso: str
    termo_versao: str
    concedido_em: datetime
    concedido_por_usuario_id: uuid.UUID
    revogado_em: datetime | None
    revogado_por_usuario_id: uuid.UUID | None
