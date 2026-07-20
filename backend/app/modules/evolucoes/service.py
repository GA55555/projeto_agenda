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
    anonimizar_com_entidades,
    entidades_do_paciente,
    verificar_sem_pii,
)
from app.modules.anonimizacao.exceptions import PIIVazadaError
from app.modules.auth.dependencies import CurrentUser
from app.modules.consentimentos.exceptions import SemConsentimentoAtivo
from app.modules.consentimentos.service import tem_consentimento_ativo
from app.modules.evolucoes.chunking import dividir_em_chunks
from app.modules.evolucoes.embeddings import canonicalizar_marcadores, gerar_embedding
from app.modules.agendamentos.models import STATUS_REALIZADO, Agendamento
from app.modules.evolucoes.exceptions import (
    AgendamentoInvalido,
    EmbeddingIndisponivel,
    PacienteInexistente,
)
from app.modules.evolucoes.models import Evolucao, EvolucaoChunk
from app.modules.evolucoes.schemas import EvolucaoCreate, EvolucaoOut
from app.modules.pacientes.models import Paciente

logger = logging.getLogger(__name__)


def _tentar_embedding(
    texto: str, entidades: list[tuple[str, str]]
) -> list[float] | None:
    """Anonimiza -> guard-rail -> canonicaliza -> embeda. None em falha/vazamento.

    Nunca deixa PII sair (§3.4): se o guard-rail detectar PII conhecida, aborta
    a chamada externa e devolve None (chunk fica pendente). Entidades ja coletadas
    (uma vez por evolucao/consulta) — sem re-query ao BD.
    """
    mascarado, _mapa = anonimizar_com_entidades(entidades, texto)
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
    if not tem_consentimento_ativo(db, dados.paciente_id):
        raise SemConsentimentoAtivo(str(dados.paciente_id))
    # Fase 7e: o agendamento vinculado precisa existir NO tenant (RLS), ser do
    # MESMO paciente e estar REALIZADO — a evolucao documenta uma sessao que
    # ocorreu, e a data do atendimento vem dele. Exigir 'realizado' impede data
    # futura/no-show e, como `apagar` so remove 'agendado', torna impossivel
    # apagar um agendamento com prontuario (conjuntos disjuntos).
    ag = db.get(Agendamento, dados.agendamento_id)
    if ag is None:
        raise AgendamentoInvalido("agendamento inexistente no tenant")
    if ag.paciente_id != dados.paciente_id:
        raise AgendamentoInvalido("agendamento pertence a outro paciente")
    if ag.status != STATUS_REALIZADO:
        raise AgendamentoInvalido(
            "a evolucao so pode ser vinculada a um atendimento realizado"
        )

    evolucao = Evolucao(
        tenant_id=user.tenant_id,
        paciente_id=dados.paciente_id,
        autor_usuario_id=user.id,
        agendamento_id=dados.agendamento_id,
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
            embedding=_tentar_embedding(texto_chunk, entidades),
        )
        db.add(chunk)
        chunks.append(chunk)
    db.flush()
    # Contagem em memoria: os chunks acabaram de ser criados nesta transacao
    # (sem query extra nem materializar vetor).
    pendentes = sum(1 for c in chunks if c.embedding is None)
    return _to_out(evolucao, len(chunks), pendentes, data_atendimento=ag.inicio)


def listar_por_paciente(db: Session, paciente_id: uuid.UUID) -> list[EvolucaoOut]:
    # OUTER JOIN unico traz a data do atendimento (agendamento.inicio) junto —
    # sem N+1; evolucoes legadas (sem vinculo) voltam com data None.
    linhas = db.execute(
        select(Evolucao, Agendamento.inicio)
        .outerjoin(Agendamento, Evolucao.agendamento_id == Agendamento.id)
        .where(Evolucao.paciente_id == paciente_id)
        .order_by(Evolucao.criado_em.desc())
    ).all()
    contagens = _contagens(db, [e.id for e, _ in linhas])
    return [
        _to_out(e, *contagens.get(e.id, (0, 0)), data_atendimento=inicio)
        for e, inicio in linhas
    ]


def obter(db: Session, evolucao_id: uuid.UUID) -> EvolucaoOut | None:
    linha = db.execute(
        select(Evolucao, Agendamento.inicio)
        .outerjoin(Agendamento, Evolucao.agendamento_id == Agendamento.id)
        .where(Evolucao.id == evolucao_id)
    ).first()
    if linha is None:
        return None
    evolucao, inicio = linha
    total, pendentes = _contagens(db, [evolucao_id]).get(evolucao_id, (0, 0))
    return _to_out(evolucao, total, pendentes, data_atendimento=inicio)


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
    vetor = _tentar_embedding(texto_novo, entidades)
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


def _to_out(
    evolucao: Evolucao,
    total_chunks: int,
    embeddings_pendentes: int,
    *,
    data_atendimento,  # sempre fornecido pelos chamadores (JOIN); sem default morto
) -> EvolucaoOut:
    return EvolucaoOut(
        id=evolucao.id,
        paciente_id=evolucao.paciente_id,
        autor_usuario_id=evolucao.autor_usuario_id,
        agendamento_id=evolucao.agendamento_id,
        data_atendimento=data_atendimento,
        texto=evolucao.texto,
        criado_em=evolucao.criado_em,
        total_chunks=total_chunks,
        embeddings_pendentes=embeddings_pendentes,
    )
