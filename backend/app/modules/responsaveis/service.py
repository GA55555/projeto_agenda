"""Regras de negocio de responsaveis legais. Nenhum acesso cross-tenant (§2.1).

O RLS restringe SELECT/UPDATE ao tenant ativo; nos INSERTs o `tenant_id` e
setado explicitamente (a policy WITH CHECK exige que case com o contexto).

Regras de ouro: §2.1, §2.2
Fase do roadmap: Fase 3
"""
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.responsaveis.exceptions import CpfDuplicado
from app.modules.responsaveis.models import ResponsavelLegal
from app.modules.responsaveis.schemas import (
    PacienteVinculadoResumo,
    ResponsavelCreate,
    ResponsavelListaOut,
    ResponsavelOut,
    ResponsavelUpdate,
)

_UNIQUE_VIOLATION = "23505"  # Postgres: unique_violation (UNIQUE(tenant_id, cpf))


def criar(db: Session, tenant_id: uuid.UUID, dados: ResponsavelCreate) -> ResponsavelLegal:
    resp = ResponsavelLegal(
        tenant_id=tenant_id,
        nome=dados.nome,
        cpf=dados.cpf,
        data_nascimento=dados.data_nascimento,
        telefone=dados.telefone,
        email=dados.email,
        endereco=dados.endereco,
    )
    db.add(resp)
    try:
        db.flush()
    except IntegrityError as exc:
        # CPF ja existe no tenant -> erro de dominio (409), nao 500.
        if getattr(exc.orig, "sqlstate", None) == _UNIQUE_VIOLATION:
            raise CpfDuplicado(dados.cpf) from exc
        raise
    return resp


def listar(db: Session) -> list[ResponsavelListaOut]:
    """Lista em duas consultas, sem N+1, incluindo criancas vinculadas."""
    responsaveis = list(
        db.execute(select(ResponsavelLegal).order_by(ResponsavelLegal.nome)).scalars()
    )
    if not responsaveis:
        return []

    # Import local evita ciclo de mappers no carregamento inicial.
    from app.modules.pacientes.models import Paciente, VinculoRespPaciente

    ids = [r.id for r in responsaveis]
    rows = db.execute(
        select(
            VinculoRespPaciente.responsavel_id,
            Paciente.id,
            Paciente.nome,
            Paciente.ativo,
        )
        .join(Paciente, Paciente.id == VinculoRespPaciente.paciente_id)
        .where(VinculoRespPaciente.responsavel_id.in_(ids))
        .order_by(Paciente.nome)
    ).all()
    por_responsavel: dict[uuid.UUID, list[PacienteVinculadoResumo]] = {rid: [] for rid in ids}
    for responsavel_id, paciente_id, nome, ativo in rows:
        por_responsavel[responsavel_id].append(
            PacienteVinculadoResumo(id=paciente_id, nome=nome, ativo=ativo)
        )

    return [
        ResponsavelListaOut(
            **ResponsavelOut.model_validate(resp).model_dump(),
            pacientes=por_responsavel[resp.id],
        )
        for resp in responsaveis
    ]


def obter(db: Session, responsavel_id: uuid.UUID) -> ResponsavelLegal | None:
    return db.get(ResponsavelLegal, responsavel_id)


def atualizar(
    db: Session, responsavel_id: uuid.UUID, dados: ResponsavelUpdate
) -> ResponsavelLegal | None:
    resp = db.get(ResponsavelLegal, responsavel_id)
    if resp is None:
        return None
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(resp, campo, valor)
    db.flush()
    return resp
