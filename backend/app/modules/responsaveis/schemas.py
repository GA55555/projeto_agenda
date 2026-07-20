"""Schemas Pydantic do modulo de responsaveis legais (§2.2).

Regras de ouro: §2.2
Fase do roadmap: Fase 3
"""
import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class ResponsavelCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    cpf: str = Field(min_length=11, max_length=14)
    data_nascimento: date | None = None
    telefone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    endereco: str | None = Field(default=None, max_length=300)

    @field_validator("cpf")
    @classmethod
    def _cpf_apenas_digitos(cls, v: str) -> str:
        # Normaliza para 11 digitos: sem isso, "111.222.333-44" e "11122233344"
        # burlariam o UNIQUE(tenant_id, cpf).
        digitos = re.sub(r"\D", "", v)
        if len(digitos) != 11:
            raise ValueError("CPF deve conter 11 digitos")
        return digitos


class ResponsavelUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    telefone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    endereco: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _nao_anular_nome(self) -> "ResponsavelUpdate":
        # `nome` e NOT NULL: enviar explicitamente null e 422, nao 500 no flush.
        if "nome" in self.model_fields_set and self.nome is None:
            raise ValueError("nome nao pode ser nulo")
        return self


class ResponsavelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    cpf: str
    data_nascimento: date | None
    telefone: str | None
    email: str | None  # response model: `str` (nao revalidar na saida; ver auth PerfilOut)
    endereco: str | None
    criado_em: datetime
