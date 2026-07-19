"""Regras de negocio de evolucoes. Nenhum acesso cross-tenant (§2.1).

Fluxo de criacao (transacao unica de `get_tenant_session`):
  1. Gate de consentimento (§2.2): paciente PRECISA de TCLE ativo (nao revogado).
  2. Grava a evolucao (texto CRU) + chunks (§3.3), embedding pendente.
  3. Passo de vetorizacao (§3.4): por chunk -> anonimiza (Fase 4) -> guard-rail ->
     canonicaliza marcadores -> OpenAI embeddings. Se a OpenAI falhar OU o
     guard-rail detectar PII, o chunk fica com embedding PENDENTE (nao vaza,
     nao perde a nota) — decisao Fase 5.

Recuperacao RAG (§3.2/§3.1/§3.4): pre-filtro por `tenant_id`+`paciente_id`
(indice B-Tree) e depois Pesquisa Exata `ORDER BY embedding <=> q` (sem indice
vetorial, §3.1). Devolve chunks CRUS; a montagem/anonimizacao do prompt final
fica para a Fase 6.

Regras de ouro: §2.1, §2.2, §3.1, §3.2, §3.4
Fase do roadmap: Fase 5
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.anonimizacao import (
    anonimizar_texto,
    entidades_do_paciente,
    verificar_sem_pii,
)
from app.modules.anonimizacao.exceptions import PIIVazadaError
from app.modules.auth.dependencies import CurrentUser
from app.modules.consentimentos.models import Consentimento
from app.modules.evolucoes.chunking import dividir_em_chunks
from app.modules.evolucoes.embeddings import canonicalizar_marcadores, gerar_embedding
from app.modules.evolucoes.exceptions import (
    EmbeddingIndisponivel,
    PacienteInexistente,
    SemConsentimentoAtivo,
)
from app.modules.evolucoes.models import Evolucao, EvolucaoChunk
from app.modules.evolucoes.schemas import EvolucaoCreate, EvolucaoOut
from app.modules.pacientes.models import Paciente

logger = logging.getLogger(__name__)


def _tem_consentimento_ativo(db: Session, paciente_id: uuid.UUID) -> bool:
    stmt = (
        select(Consentimento.id)
        .where(Consentimento.paciente_id == paciente_id)
        .where(Consentimento.revogado_em.is_(None))
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def _tentar_embedding(
    db: Session, paciente_id: uuid.UUID, texto_chunk: str, entidades: list[tuple[str, str]]
) -> list[float] | None:
    """Anonimiza -> guard-rail -> canonicaliza -> embeda. None em falha/vazamento.

    Nunca deixa PII sair (§3.4): se o guard-rail detectar PII conhecida, aborta
    a chamada externa e devolve None (chunk fica pendente).
    """
    mascarado, _mapa = anonimizar_texto(db, paciente_id, texto_chunk)
    try:
        verificar_sem_pii(mascarado, entidades)  # §3.4 #4 (guard-rail nos embeddings)
    except PIIVazadaError:
        logger.warning("guard-rail barrou embedding: PII conhecida escapou; chunk pendente")
        return None
    canonico = canonicalizar_marcadores(mascarado)
    try:
        return gerar_embedding(canonico)
    except EmbeddingIndisponivel as exc:
        logger.warning("embedding indisponivel (%s); chunk pendente", exc)
        return None


def criar_evolucao(db: Session, user: CurrentUser, dados: EvolucaoCreate) -> EvolucaoOut:
    if db.get(Paciente, dados.paciente_id) is None:
        raise PacienteInexistente(str(dados.paciente_id))
    if not _tem_consentimento_ativo(db, dados.paciente_id):
        raise SemConsentimentoAtivo(str(dados.paciente_id))

    evolucao = Evolucao(
        tenant_id=user.tenant_id,
        paciente_id=dados.paciente_id,
        autor_usuario_id=user.id,
        texto=dados.texto,
    )
    db.add(evolucao)
    db.flush()  # materializa evolucao.id para os FKs dos chunks

    textos = dividir_em_chunks(dados.texto)
    entidades = entidades_do_paciente(db, dados.paciente_id)  # p/ o guard-rail
    chunks: list[EvolucaoChunk] = []
    for ordem, texto_chunk in enumerate(textos):
        chunk = EvolucaoChunk(
            tenant_id=user.tenant_id,
            paciente_id=dados.paciente_id,
            evolucao_id=evolucao.id,
            ordem=ordem,
            texto_chunk=texto_chunk,
            embedding=_tentar_embedding(db, dados.paciente_id, texto_chunk, entidades),
        )
        db.add(chunk)
        chunks.append(chunk)
    db.flush()
    # Contagem em memoria: os chunks acabaram de ser criados nesta transacao
    # (sem query extra nem materializar vetor).
    pendentes = sum(1 for c in chunks if c.embedding is None)
    return _to_out(evolucao, len(chunks), pendentes)


def listar_por_paciente(db: Session, paciente_id: uuid.UUID) -> list[EvolucaoOut]:
    evolucoes = list(
        db.execute(
            select(Evolucao)
            .where(Evolucao.paciente_id == paciente_id)
            .order_by(Evolucao.criado_em.desc())
        ).scalars()
    )
    contagens = _contagens(db, [e.id for e in evolucoes])
    return [_to_out(e, *contagens.get(e.id, (0, 0))) for e in evolucoes]


def obter(db: Session, evolucao_id: uuid.UUID) -> EvolucaoOut | None:
    evolucao = db.get(Evolucao, evolucao_id)
    if evolucao is None:
        return None
    total, pendentes = _contagens(db, [evolucao_id]).get(evolucao_id, (0, 0))
    return _to_out(evolucao, total, pendentes)


def buscar_contexto(
    db: Session,
    tenant_id: uuid.UUID,
    paciente_id: uuid.UUID,
    texto_novo: str,
    entidades: list[tuple[str, str]],
    k: int = 5,
) -> list[str]:
    """Chunks mais relevantes do paciente (RAG). Consumido pela Fase 6.

    Filtragem hibrida OBRIGATORIA (§3.2): pre-filtra por tenant+paciente antes
    do calculo de distancia; Pesquisa Exata sem indice (§3.1). Devolve texto CRU.
    """
    vetor = _tentar_embedding(db, paciente_id, texto_novo, entidades)
    if vetor is None:
        return []  # sem embedding de consulta -> degrada para sem-RAG
    stmt = (
        select(EvolucaoChunk.texto_chunk)
        .where(EvolucaoChunk.tenant_id == tenant_id)      # §3.2 (indice B-Tree)
        .where(EvolucaoChunk.paciente_id == paciente_id)  # §3.2
        .where(EvolucaoChunk.embedding.isnot(None))
        .order_by(EvolucaoChunk.embedding.cosine_distance(vetor))  # §3.1 exata
        .limit(k)
    )
    return list(db.execute(stmt).scalars())


def _contagens(
    db: Session, evolucao_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, int]]:
    """(total_chunks, embeddings_pendentes) por evolucao — via COUNT, sem puxar
    o vetor. Uma unica query agregada para todas as evolucoes (evita N+1)."""
    if not evolucao_ids:
        return {}
    stmt = (
        select(
            EvolucaoChunk.evolucao_id,
            func.count().label("total"),
            func.count().filter(EvolucaoChunk.embedding.is_(None)).label("pendentes"),
        )
        .where(EvolucaoChunk.evolucao_id.in_(evolucao_ids))
        .group_by(EvolucaoChunk.evolucao_id)
    )
    return {row.evolucao_id: (row.total, row.pendentes) for row in db.execute(stmt)}


def _to_out(evolucao: Evolucao, total_chunks: int, embeddings_pendentes: int) -> EvolucaoOut:
    return EvolucaoOut(
        id=evolucao.id,
        paciente_id=evolucao.paciente_id,
        autor_usuario_id=evolucao.autor_usuario_id,
        texto=evolucao.texto,
        criado_em=evolucao.criado_em,
        total_chunks=total_chunks,
        embeddings_pendentes=embeddings_pendentes,
    )
