"""Schemas Pydantic do modulo de pacientes e vinculos (§2.2).

Invariante do DoD (Fase 3): impossivel criar paciente sem responsavel legal e
sem TCLE. Imposto ja no schema: `vinculos` tem `min_length=1` e `consentimento`
e obrigatorio. Um `model_validator` garante que o TCLE aponta para um dos
responsaveis vinculados.

Regras de ouro: §2.2
Fase do roadmap: Fase 3
"""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.consentimentos.schemas import ConsentimentoCreate
from app.modules.pacientes.models import TIPOS_VINCULO
from app.modules.responsaveis.schemas import ResponsavelOut


class VinculoCreate(BaseModel):
    responsavel_id: uuid.UUID
    tipo_vinculo: str
    detem_guarda: bool = False
    principal: bool = False

    @field_validator("tipo_vinculo")
    @classmethod
    def _tipo_valido(cls, v: str) -> str:
        if v not in TIPOS_VINCULO:
            raise ValueError(f"tipo_vinculo invalido; use um de {TIPOS_VINCULO}")
        return v


class VinculoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    responsavel_id: uuid.UUID
    paciente_id: uuid.UUID
    tipo_vinculo: str
    detem_guarda: bool
    principal: bool


class PacienteCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    data_nascimento: date
    sexo: str | None = Field(default=None, max_length=20)
    observacoes_gerais: str | None = Field(default=None, max_length=1000)
    vinculos: list[VinculoCreate] = Field(min_length=1)  # >=1 responsavel (§2.2)
    consentimento: ConsentimentoCreate  # TCLE obrigatorio no mesmo ato (§2.2)

    @model_validator(mode="after")
    def _tcle_aponta_para_vinculo(self) -> "PacienteCreate":
        ids = {v.responsavel_id for v in self.vinculos}
        if self.consentimento.responsavel_id not in ids:
            raise ValueError(
                "consentimento.responsavel_id deve ser um dos responsaveis vinculados"
            )
        return self


class PacienteUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    sexo: str | None = Field(default=None, max_length=20)
    observacoes_gerais: str | None = Field(default=None, max_length=1000)
    ativo: bool | None = None

    @model_validator(mode="after")
    def _nao_anular_nao_nulos(self) -> "PacienteUpdate":
        # `nome` e `ativo` sao NOT NULL: null explicito e 422, nao 500 no flush.
        for campo in ("nome", "ativo"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} nao pode ser nulo")
        return self


class PacienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    data_nascimento: date
    sexo: str | None
    observacoes_gerais: str | None
    ativo: bool
    criado_em: datetime


class VinculoComResponsavel(VinculoOut):
    responsavel: ResponsavelOut


class PacienteDetalhado(PacienteOut):
    vinculos: list[VinculoComResponsavel]
