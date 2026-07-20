"""Modelo da auditoria imutavel (append-only) — §2.2.

Log GENERICO de eventos sensiveis: cobre os eventos mandatados pela §2.2
(revogacao de consentimento, alteracao de guarda legal) e e extensivel a novos
tipos SEM nova migration (o `tipo_evento` e String livre; os valores canonicos
ficam em `TIPOS_EVENTO`).

Imutabilidade imposta no MOTOR da BD (§2.1/§2.2), nao na aplicacao:
  - o role de app recebe apenas INSERT/SELECT (sem UPDATE/DELETE);
  - um trigger BEFORE UPDATE OR DELETE levanta excecao (barra ate o dono).
Aplicado na migration.

Regras de ouro: §2.1, §2.2
Fase do roadmap: Fase 3
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Tipos de evento canonicos mandatados pela §2.2 (nao exaustivo — String livre).
TIPO_CONSENTIMENTO_REVOGADO = "consentimento_revogado"
TIPO_GUARDA_ALTERADA = "guarda_alterada"
# Fase 7c: troca do identificador de login e mutacao sensivel -> auditavel.
TIPO_PERFIL_EMAIL_ALTERADO = "perfil_email_alterado"
# Fase 7e: exclusoes/arquivamento sao mutacoes sensiveis -> auditaveis.
TIPO_AGENDAMENTO_APAGADO = "agendamento_apagado"
TIPO_PACIENTE_APAGADO = "paciente_apagado"
TIPO_PACIENTE_ARQUIVADO = "paciente_arquivado"
TIPO_PACIENTE_REATIVADO = "paciente_reativado"
TIPOS_EVENTO = (
    TIPO_CONSENTIMENTO_REVOGADO,
    TIPO_GUARDA_ALTERADA,
    TIPO_PERFIL_EMAIL_ALTERADO,
    TIPO_AGENDAMENTO_APAGADO,
    TIPO_PACIENTE_APAGADO,
    TIPO_PACIENTE_ARQUIVADO,
    TIPO_PACIENTE_REATIVADO,
)


class Auditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tipo_evento: Mapped[str] = mapped_column(String(60), nullable=False)
    entidade: Mapped[str] = mapped_column(String(60), nullable=False)
    entidade_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ator_usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
