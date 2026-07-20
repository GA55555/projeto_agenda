"""Schemas Pydantic do modulo de agendamentos (Fase 3.5).

`fim > inicio` e validado aqui (best-effort) e tambem no BD (CHECK). A
nao-sobreposicao e imposta so no BD (EXCLUDE, §2.1) — a API traduz a violacao
em 409.

Regras de ouro: §2.1
Fase do roadmap: Fase 3.5
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.agendamentos.models import STATUS_AGENDAMENTO


class Recorrencia(BaseModel):
    # "esse dia e esse horario" repetido. Semanal/quinzenal preservam o dia da
    # semana; mensal preserva a DATA (mesmo dia do mes) — ver rotulo na SPA.
    frequencia: Literal["semanal", "quinzenal", "mensal"]


class AgendamentoCreate(BaseModel):
    paciente_id: uuid.UUID
    # AwareDatetime: exige timezone — evita horario ambiguo num `timestamptz`.
    inicio: AwareDatetime
    fim: AwareDatetime
    tipo: str | None = Field(default=None, max_length=40)
    observacao: str | None = Field(default=None, max_length=1000)
    # Se presente, cria a serie de ocorrencias futuras (Fase 7f).
    recorrencia: Recorrencia | None = None

    @model_validator(mode="after")
    def _fim_apos_inicio(self) -> "AgendamentoCreate":
        if self.fim <= self.inicio:
            raise ValueError("fim deve ser posterior a inicio")
        return self


class AgendamentoUpdate(BaseModel):
    inicio: AwareDatetime | None = None
    fim: AwareDatetime | None = None
    status: str | None = None
    tipo: str | None = Field(default=None, max_length=40)
    observacao: str | None = Field(default=None, max_length=1000)

    @field_validator("status")
    @classmethod
    def _status_valido(cls, v: str | None) -> str | None:
        if v is not None and v not in STATUS_AGENDAMENTO:
            raise ValueError(f"status invalido; use um de {STATUS_AGENDAMENTO}")
        return v

    @model_validator(mode="after")
    def _coerencia(self) -> "AgendamentoUpdate":
        # `status` e NOT NULL: null explicito e 422, nao 500 no flush.
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("status nao pode ser nulo")
        # Se ambos vierem, valida a ordem (o BD e o backstop para updates parciais).
        if self.inicio is not None and self.fim is not None and self.fim <= self.inicio:
            raise ValueError("fim deve ser posterior a inicio")
        return self


class CancelamentoIn(BaseModel):
    motivo: str | None = None


class AgendamentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    paciente_id: uuid.UUID
    inicio: datetime
    fim: datetime
    status: str
    tipo: str | None
    observacao: str | None
    motivo_cancelamento: str | None
    serie_id: uuid.UUID | None  # != None -> faz parte de uma recorrencia (Fase 7f)
    criado_em: datetime


class AgendamentoCriadoOut(AgendamentoOut):
    """Resposta do POST: o atendimento criado + resumo da serie (Fase 7f).

    `serie_criados` = ocorrencias futuras criadas ALEM desta; `serie_pulados_datas`
    = inicios das ocorrencias puladas por conflito (a SPA lista as datas p/ o
    usuario saber onde ficaram lacunas). Vazios em agendamento avulso.
    """

    serie_criados: int = 0
    serie_pulados_datas: list[datetime] = []
