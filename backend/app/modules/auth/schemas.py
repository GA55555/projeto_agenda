"""Schemas Pydantic do modulo de autenticacao.

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 2
"""
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    # Response model: serializa e-mail JA gravado (confiavel) -> `str`, nao
    # `EmailStr`. Revalidar na saida quebra e-mails validos-mas-reservados
    # (ex.: `.local`), que o email-validator rejeita. EmailStr fica so na entrada.
    email: str
    nome: str
    papel: str
    tenant_id: uuid.UUID


class PerfilOut(BaseModel):
    """Contexto do utilizador logado para o menu de perfil da SPA (Fase 7c)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    papel: str
    nome: str
    email: str  # str, nao EmailStr (ver UsuarioOut) — nao revalidar na saida


class PerfilUpdate(BaseModel):
    """Edicao do proprio perfil (Fase 7c). Campos opcionais: so o enviado muda.

    `EmailStr` na ENTRADA (valida o formato); a saida (`PerfilOut`) usa `str`
    para nao rejeitar TLDs reservados ja gravados (licao do /auth/me 500).

    Trocar o e-mail = trocar o identificador de login -> exige `senha_atual`
    (re-autenticacao; verificada no service) e gera evento de auditoria (§2.2).
    """

    nome: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    # Obrigatoria QUANDO o email muda (checado no service, que conhece o atual).
    senha_atual: str | None = None

    @field_validator("email")
    @classmethod
    def _email_minusculo(cls, v: str | None) -> str | None:
        # E-mail sempre gravado em minusculas: EmailStr so normaliza o dominio,
        # e o login casa por lower() — sem isto, 'Ana@x' gravado trancaria a
        # conta e burlaria o UNIQUE contra 'ana@x'.
        return v.lower() if v is not None else v

    @model_validator(mode="after")
    def _nao_anular_enviados(self) -> "PerfilUpdate":
        # Enviar o campo explicitamente como null e 422 (sao NOT NULL no BD).
        for campo in ("nome", "email"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"{campo} nao pode ser nulo")
        return self


class SenhaUpdate(BaseModel):
    """Troca de senha: exige a senha atual (Fase 7c, §4.1)."""

    senha_atual: str = Field(min_length=1)
    senha_nova: str = Field(min_length=8, max_length=72)

    @field_validator("senha_nova")
    @classmethod
    def _limite_do_bcrypt_em_bytes(cls, v: str) -> str:
        # O limite do bcrypt e 72 BYTES, nao caracteres: acentos/emoji em UTF-8
        # ocupam 2-4 bytes e o bcrypt >= 5 levanta ValueError em vez de truncar
        # -> viraria 500. Barrar aqui com 422 e mensagem clara.
        if len(v.encode("utf-8")) > 72:
            raise ValueError("senha muito longa: maximo de 72 bytes em UTF-8")
        return v
