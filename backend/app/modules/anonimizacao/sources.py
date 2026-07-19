"""Fonte das entidades PII CADASTRADAS que alimentam o autômato (§2.3).

Monta a lista de termos conhecidos do contexto do paciente — nome do paciente,
nomes/CPF/telefone/e-mail/endereco dos responsaveis vinculados e o nome da
clinica (tenant). Tudo lido SOB A SESSAO COM RLS (§2.1): a consulta so enxerga
o que pertence ao tenant ativo; nenhum termo de outro locatario entra no mapa.

Alem do nome completo, cada nome e quebrado em tokens (>= 3 letras, fora de
conectivos) — assim a nota que cita so o primeiro nome do paciente ("Pedro")
tambem e mascarada. Recall alto e desejavel: o principio e risco-zero de PII
(§0.3), e um falso-positivo apenas mascara uma palavra a mais.

Regras de ouro: §2.3, §2.1
Fase do roadmap: Fase 4
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pacientes.models import Paciente, VinculoRespPaciente
from app.modules.responsaveis.models import ResponsavelLegal
from app.modules.tenants.models import Tenant

# Categorias (prefixo do marcador).
CAT_PERSON = "PERSON"
CAT_ORG = "ORG"
CAT_ADDRESS = "ADDRESS"
CAT_CPF = "CPF"
CAT_PHONE = "PHONE"
CAT_EMAIL = "EMAIL"

# Conectivos de nomes proprios que nao devem virar termo isolado.
_CONECTIVOS = {"de", "da", "do", "das", "dos", "e"}


def _tokens_de_nome(nome: str) -> list[str]:
    """Nome completo + tokens significativos (>= 3 letras, fora de conectivos)."""
    termos = [nome]
    for parte in nome.split():
        p = parte.strip()
        if len(p) >= 3 and p.lower() not in _CONECTIVOS:
            termos.append(p)
    return termos


def coletar_entidades(db: Session, paciente_id: uuid.UUID) -> list[tuple[str, str]]:
    """Devolve pares (termo, categoria) das PII cadastradas do paciente (§2.3).

    A sessao `db` DEVE carregar o contexto de tenant (RLS ativo). Nao ha filtro
    manual por tenant aqui — o motor da BD garante o isolamento (§2.1).
    """
    entidades: list[tuple[str, str]] = []

    paciente = db.get(Paciente, paciente_id)
    if paciente is None:
        return entidades  # fora do tenant ou inexistente -> nada a mascarar

    for termo in _tokens_de_nome(paciente.nome):
        entidades.append((termo, CAT_PERSON))

    # Responsaveis vinculados (N:N) — join pelo vinculo, ainda sob RLS.
    stmt = (
        select(ResponsavelLegal)
        .join(
            VinculoRespPaciente,
            VinculoRespPaciente.responsavel_id == ResponsavelLegal.id,
        )
        .where(VinculoRespPaciente.paciente_id == paciente_id)
    )
    for resp in db.execute(stmt).scalars().unique():
        for termo in _tokens_de_nome(resp.nome):
            entidades.append((termo, CAT_PERSON))
        if resp.cpf:
            entidades.append((resp.cpf, CAT_CPF))
        if resp.telefone:
            entidades.append((resp.telefone, CAT_PHONE))
        if resp.email:
            entidades.append((resp.email, CAT_EMAIL))
        if resp.endereco:
            entidades.append((resp.endereco, CAT_ADDRESS))

    # Nome da clinica (tenant): RLS restringe a linha do proprio locatario.
    tenant = db.get(Tenant, paciente.tenant_id)
    if tenant is not None and tenant.nome:
        entidades.append((tenant.nome, CAT_ORG))

    # Remove duplicatas preservando a ordem.
    vistos: set[tuple[str, str]] = set()
    unicas: list[tuple[str, str]] = []
    for e in entidades:
        if e not in vistos:
            vistos.add(e)
            unicas.append(e)
    return unicas
