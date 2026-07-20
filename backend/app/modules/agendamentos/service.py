"""Regras de negocio de agendamentos. Nenhum acesso cross-tenant (§2.1).

O RLS restringe SELECT/UPDATE ao tenant ativo; no INSERT o `tenant_id` e setado
explicitamente. A nao-sobreposicao e imposta no BD (EXCLUDE); aqui apenas
traduzimos a violacao (SQLSTATE 23P01) em `HorarioIndisponivel` -> 409.

Regras de ouro: §2.1
Fase do roadmap: Fase 3.5
"""
import calendar
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.modules.agendamentos.exceptions import (
    HorarioIndisponivel,
    IntervaloInvalido,
    NaoRecorrente,
    PacienteInexistente,
    TransicaoInvalida,
)
from app.modules.agendamentos.models import STATUS_AGENDADO, STATUS_CANCELADO, Agendamento
from app.modules.agendamentos.schemas import AgendamentoCreate, AgendamentoUpdate
from app.modules.pacientes.models import Paciente

# exclusion_violation — sobreposicao barrada pela constraint EXCLUDE.
_EXCLUSION_VIOLATION = "23P01"
# foreign_key_violation — agendamento referenciado por evolucao (FK RESTRICT).
_FK_VIOLATION = "23503"
# Horizonte da recorrencia: ~6 meses de ocorrencias futuras (Fase 7f).
_HORIZONTE_DIAS = 183


def _add_meses(dt: datetime, n: int) -> datetime:
    """dt + n meses, fixando o dia no ultimo dia do mes quando estoura (ex.: 31)."""
    total = dt.month - 1 + n
    ano = dt.year + total // 12
    mes = total % 12 + 1
    dia = min(dt.day, calendar.monthrange(ano, mes)[1])
    return dt.replace(year=ano, month=mes, day=dia)


def _ocorrencia(anchor: datetime, frequencia: str, k: int) -> datetime:
    """k-esima ocorrencia (k>=1) a partir do ANCHOR original — nunca encadeia da
    ocorrencia anterior ja clampada (senao a cadencia mensal derivava: 31/01 ->
    28/02 -> 28/03 em vez de voltar a 31/03)."""
    if frequencia == "semanal":
        return anchor + timedelta(weeks=k)
    if frequencia == "quinzenal":
        return anchor + timedelta(weeks=2 * k)
    return _add_meses(anchor, k)  # mensal


def validar_transicao_status(atual: str, novo: str) -> None:
    """Maquina de estados do agendamento no BACKEND (Fase 7c), nao so na UI.

    Regras: `cancelado` e TERMINAL e so se entra nele pela rota /cancelar (que
    carrega o motivo e a semantica soft) — o PATCH nao entra nem sai de
    cancelado. Entre agendado/realizado/falta a transicao e livre (correcao de
    apontamento e legitima). No-op (novo == atual) e permitido.

    Sem isto, um PATCH direto faria cancelado->realizado (registro 'realizado'
    com motivo_cancelamento preenchido) e corromperia os agregados do dashboard.
    """
    if novo == atual:
        return
    if atual == STATUS_CANCELADO:
        raise TransicaoInvalida("agendamento cancelado e terminal; crie um novo")
    if novo == STATUS_CANCELADO:
        raise TransicaoInvalida("para cancelar, use a rota de cancelamento")


def _flush_traduzindo(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) == _EXCLUSION_VIOLATION:
            raise HorarioIndisponivel() from exc
        raise


def _paciente_existe(db: Session, paciente_id: uuid.UUID) -> bool:
    # RLS: so encontra se o paciente for do tenant ativo.
    stmt = select(Paciente.id).where(Paciente.id == paciente_id)
    return db.execute(stmt).scalar_one_or_none() is not None


def criar(
    db: Session, tenant_id: uuid.UUID, dados: AgendamentoCreate
) -> tuple[Agendamento, int, list[datetime]]:
    """Cria o atendimento; se `recorrencia`, materializa a serie futura.

    Retorna (primario, serie_criados, datas_puladas). O PRIMARIO segue a regra de
    hoje: conflito -> 409. As ocorrencias futuras sao best-effort: cada uma num
    SAVEPOINT; se colidir (EXCLUDE 23P01) pula aquela cadencia (Fase 7f). A
    frequencia fica gravada em `serie_frequencia` (a REGRA sobrevive p/ a Fase 8).
    """
    if not _paciente_existe(db, dados.paciente_id):
        raise PacienteInexistente(str(dados.paciente_id))
    ag = Agendamento(
        tenant_id=tenant_id,
        paciente_id=dados.paciente_id,
        inicio=dados.inicio,
        fim=dados.fim,
        tipo=dados.tipo,
        observacao=dados.observacao,
    )
    db.add(ag)
    _flush_traduzindo(db)  # conflito do primario -> 409, como no avulso

    if dados.recorrencia is None:
        return ag, 0, []

    freq = dados.recorrencia.frequencia
    serie_id = uuid.uuid4()
    ag.serie_id = serie_id
    ag.serie_frequencia = freq
    db.flush()

    duracao = dados.fim - dados.inicio
    limite = dados.inicio + timedelta(days=_HORIZONTE_DIAS)
    criados = 0
    datas_puladas: list[datetime] = []
    k = 1
    while True:
        inicio_oc = _ocorrencia(dados.inicio, freq, k)  # sempre do ANCHOR
        if inicio_oc > limite:
            break
        oc = Agendamento(
            tenant_id=tenant_id,
            paciente_id=dados.paciente_id,
            inicio=inicio_oc,
            fim=inicio_oc + duracao,
            tipo=dados.tipo,
            observacao=dados.observacao,
            serie_id=serie_id,
            serie_frequencia=freq,
        )
        try:
            with db.begin_nested():  # SAVEPOINT: rollback isolado no conflito
                db.add(oc)
                db.flush()
            criados += 1
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == _EXCLUSION_VIOLATION:
                datas_puladas.append(inicio_oc)  # horario ocupado -> pula
            else:
                # Erro inesperado: para a serie (o SAVEPOINT ja reverteu esta
                # ocorrencia) mas PRESERVA o primario e as ja criadas, em vez de
                # deixar o rollback da transacao apagar tudo.
                logger.warning("recorrencia interrompida por erro inesperado: %s", exc)
                break
        k += 1

    return ag, criados, datas_puladas


def desfazer_recorrencia(db: Session, user, agendamento_id: uuid.UUID) -> int | None:
    """Para a recorrencia a partir do atendimento aberto (Fase 7f).

    MANTEM a ocorrencia aberta (vira avulsa); remove as OUTRAS futuras ainda
    'agendado' da serie; passadas/realizadas ficam. Evolucao so vincula
    'realizado', entao nenhuma futura 'agendado' tem prontuario — o DELETE nunca
    esbarra no FK. Ao fim, DISSOLVE a serie (`serie_id`/`serie_frequencia` = NULL
    em tudo que sobrou) — o botao "desfazer" some das ocorrencias restantes e uma
    segunda chamada da NaoRecorrente. Auditavel (§2.2). Retorna quantas removeu,
    ou None se o agendamento nao existe; NaoRecorrente se nao faz parte de serie.
    """
    ag = db.get(Agendamento, agendamento_id)
    if ag is None:
        return None
    if ag.serie_id is None:
        raise NaoRecorrente(str(agendamento_id))

    serie_id = ag.serie_id
    agora = datetime.now(timezone.utc)
    # Remove as OUTRAS futuras 'agendado' (a aberta e preservada como avulsa).
    removidos = db.execute(
        delete(Agendamento).where(
            Agendamento.serie_id == serie_id,
            Agendamento.status == STATUS_AGENDADO,
            Agendamento.inicio > agora,
            Agendamento.id != ag.id,
        )
    ).rowcount
    # Dissolve a serie no que sobrou (inclui a aberta).
    db.execute(
        update(Agendamento)
        .where(Agendamento.serie_id == serie_id)
        .values(serie_id=None, serie_frequencia=None)
    )

    from app.modules.audit import service as audit_service
    from app.modules.audit.models import TIPO_RECORRENCIA_DESFEITA

    audit_service.registrar_evento(
        db,
        tenant_id=user.tenant_id,
        tipo_evento=TIPO_RECORRENCIA_DESFEITA,
        entidade="agendamento",
        entidade_id=ag.id,
        ator_usuario_id=user.id,
        payload={"serie_id": str(serie_id), "removidos": removidos},
    )
    db.flush()
    return removidos


def listar(
    db: Session,
    *,
    de: datetime | None = None,
    ate: datetime | None = None,
    paciente_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[Agendamento]:
    stmt = select(Agendamento).order_by(Agendamento.inicio)
    if de is not None:
        stmt = stmt.where(Agendamento.inicio >= de)
    if ate is not None:
        stmt = stmt.where(Agendamento.inicio < ate)
    if paciente_id is not None:
        stmt = stmt.where(Agendamento.paciente_id == paciente_id)
    if status is not None:
        stmt = stmt.where(Agendamento.status == status)
    return list(db.execute(stmt).scalars())


def obter(db: Session, agendamento_id: uuid.UUID) -> Agendamento | None:
    return db.get(Agendamento, agendamento_id)


def atualizar(
    db: Session, agendamento_id: uuid.UUID, dados: AgendamentoUpdate
) -> Agendamento | None:
    ag = db.get(Agendamento, agendamento_id)
    if ag is None:
        return None
    campos = dados.model_dump(exclude_unset=True)
    if "status" in campos:
        validar_transicao_status(ag.status, campos["status"])
    for campo, valor in campos.items():
        setattr(ag, campo, valor)
    # Update parcial: valida o intervalo EFETIVO (novo + valores atuais) antes do
    # flush, para dar 422 em vez de estourar o CHECK do BD como 500.
    if ag.fim <= ag.inicio:
        raise IntervaloInvalido()
    _flush_traduzindo(db)  # reagendamento tambem passa pelo EXCLUDE
    return ag


def cancelar(
    db: Session, agendamento_id: uuid.UUID, motivo: str | None
) -> Agendamento | None:
    ag = db.get(Agendamento, agendamento_id)
    if ag is None:
        return None
    # So se cancela o que esta AGENDADO: re-cancelar sobrescreveria o motivo
    # original (historico que o soft-cancel existe para preservar) e cancelar
    # um realizado/falta apagaria um apontamento ja feito.
    if ag.status != STATUS_AGENDADO:
        raise TransicaoInvalida(f"nao e possivel cancelar um agendamento '{ag.status}'")
    ag.status = STATUS_CANCELADO
    ag.motivo_cancelamento = motivo
    db.flush()  # cancelar libera o horario (fica fora do EXCLUDE)
    return ag


def apagar(db: Session, user, agendamento_id: uuid.UUID) -> bool:
    """Apaga um agendamento (Fase 7e) — SO para corrigir erro de lancamento.

    Regras: apenas status 'agendado' (realizado/falta/cancelado sao historico
    que alimenta o dashboard). Evolucao so vincula atendimento REALIZADO, entao
    um 'agendado' nunca tem prontuario — mas, por defesa em profundidade, se o
    FK RESTRICT (§2.1) barrar o DELETE, traduzimos em 409 (nunca 500). Exclusao
    e mutacao sensivel -> evento de auditoria na MESMA transacao (§2.2). Retorna
    False se nao encontrado.
    """
    ag = db.get(Agendamento, agendamento_id)
    if ag is None:
        return False
    if ag.status != STATUS_AGENDADO:
        raise TransicaoInvalida(f"nao e possivel apagar um agendamento '{ag.status}'")

    from app.modules.audit import service as audit_service
    from app.modules.audit.models import TIPO_AGENDAMENTO_APAGADO

    audit_service.registrar_evento(
        db,
        tenant_id=user.tenant_id,
        tipo_evento=TIPO_AGENDAMENTO_APAGADO,
        entidade="agendamento",
        entidade_id=ag.id,
        ator_usuario_id=user.id,
        payload={
            "paciente_id": str(ag.paciente_id),
            "inicio": ag.inicio.isoformat(),
            "fim": ag.fim.isoformat(),
        },
    )
    db.delete(ag)
    try:
        db.flush()
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) == _FK_VIOLATION:
            raise TransicaoInvalida(
                "agendamento com evolucao vinculada nao pode ser apagado"
            ) from exc
        raise
    return True
