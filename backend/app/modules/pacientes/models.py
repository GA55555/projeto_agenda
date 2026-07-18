"""Modelos do paciente (menor) e do vinculo N:N com responsaveis legais (§2.2).

Tabelas clinicas: `tenant_id` + RLS/FORCE (na migration). Um paciente NUNCA
existe sem ao menos um responsavel legal — o invariante e imposto na criacao
(service, transacao unica) e reforçado pela tabela de vinculo.

Isolamento no MOTOR (§2.1): o vinculo referencia o responsavel/paciente por
CHAVE COMPOSTA `(tenant_id, id)` — a BD garante que ambos os lados do vinculo
pertencem ao MESMO tenant, sem depender de checagem na aplicacao. Exige
`UNIQUE(tenant_id, id)` nos pais (alvo do FK composto).

`vinculos_resp_paciente` (N:N) carrega o tipo do vinculo, se o responsavel
detem a guarda e se e o responsavel principal. Alteracao de guarda e evento
auditavel/imutavel (§2.2) — registrado em `auditoria`.

Regras de ouro: §2.1, §2.2
Fase do roadmap: Fase 3
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKeyConstraint, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.responsaveis.models import ResponsavelLegal  # noqa: F401 (registra o mapper)

# Vocabulario controlado do tipo de vinculo (CHECK na migration).
TIPOS_VINCULO = ("mae", "pai", "tutor", "avo", "outro")


class Paciente(Base):
    __tablename__ = "pacientes"
    # Alvo do FK composto (tenant_id, id) vindo dos vinculos/consentimentos (§2.1).
    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_pacientes_tenant_id_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    data_nascimento: Mapped[date] = mapped_column(Date, nullable=False)
    sexo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    observacoes_gerais: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    # Somente leitura (o vinculo e criado setando as colunas FK, nao via relacao).
    # Carregado sob demanda (selectinload no service `obter`); nao eager por padrao.
    vinculos: Mapped[list["VinculoRespPaciente"]] = relationship(
        back_populates="paciente",
        primaryjoin="Paciente.id == VinculoRespPaciente.paciente_id",
        foreign_keys="[VinculoRespPaciente.paciente_id]",
        viewonly=True,
    )


class VinculoRespPaciente(Base):
    __tablename__ = "vinculos_resp_paciente"
    __table_args__ = (
        # FK compostos: garantem que responsavel e paciente sao do MESMO tenant (§2.1).
        ForeignKeyConstraint(
            ["tenant_id", "responsavel_id"],
            ["responsaveis_legais.tenant_id", "responsaveis_legais.id"],
            ondelete="RESTRICT",
            name="fk_vinculos_resp_paciente_responsavel",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "paciente_id"],
            ["pacientes.tenant_id", "pacientes.id"],
            ondelete="RESTRICT",
            name="fk_vinculos_resp_paciente_paciente",
        ),
        UniqueConstraint(
            "tenant_id", "responsavel_id", "paciente_id",
            name="uq_vinculos_resp_paciente_tenant_id_responsavel_id_paciente_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    responsavel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    paciente_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tipo_vinculo: Mapped[str] = mapped_column(String(20), nullable=False)
    detem_guarda: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    principal: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    # Relacoes somente-leitura; join explicito por id (o FK composto e do BD, §2.1).
    paciente: Mapped["Paciente"] = relationship(
        back_populates="vinculos",
        primaryjoin="VinculoRespPaciente.paciente_id == Paciente.id",
        foreign_keys=[paciente_id],
        viewonly=True,
    )
    responsavel: Mapped["ResponsavelLegal"] = relationship(
        primaryjoin="VinculoRespPaciente.responsavel_id == ResponsavelLegal.id",
        foreign_keys=[responsavel_id],
        viewonly=True,
    )
