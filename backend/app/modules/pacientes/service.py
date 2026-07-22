"""Regras de negocio de pacientes. Nenhum acesso cross-tenant (§2.1).

`criar_paciente` impoe o invariante do DoD (§2.2): paciente + >=1 vinculo com
responsavel + TCLE sao inseridos numa UNICA transacao (a de `get_tenant_session`).
Se qualquer parte falhar, nada e persistido — impossivel paciente orfao ou sem
consentimento.

Regras de ouro: §2.1, §2.2
Fase do roadmap: Fase 3
"""
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.agendamentos.models import STATUS_AGENDADO, Agendamento
from app.modules.auth.dependencies import CurrentUser
from app.modules.consentimentos.models import Consentimento
from app.modules.evolucoes.models import Evolucao
from app.modules.pacientes.exceptions import (
    PacienteComAgendamentosFuturos,
    PacienteComProntuario,
    ResponsavelInexistente,
)
from app.modules.pacientes.models import Paciente, VinculoRespPaciente
from app.modules.pacientes.schemas import PacienteCreate, PacienteUpdate
from app.modules.responsaveis.models import ResponsavelLegal


def criar_paciente(db: Session, user: CurrentUser, dados: PacienteCreate) -> Paciente:
    # Todos os responsaveis referenciados precisam existir NO tenant (RLS filtra).
    ids = {v.responsavel_id for v in dados.vinculos}
    encontrados = set(
        db.execute(
            select(ResponsavelLegal.id).where(ResponsavelLegal.id.in_(ids))
        ).scalars()
    )
    if encontrados != ids:
        raise ResponsavelInexistente(str(ids - encontrados))

    paciente = Paciente(
        tenant_id=user.tenant_id,
        nome=dados.nome,
        data_nascimento=dados.data_nascimento,
        sexo=dados.sexo,
        observacoes_gerais=dados.observacoes_gerais,
    )
    db.add(paciente)
    db.flush()  # materializa paciente.id para os FKs

    for v in dados.vinculos:
        db.add(
            VinculoRespPaciente(
                tenant_id=user.tenant_id,
                paciente_id=paciente.id,
                responsavel_id=v.responsavel_id,
                tipo_vinculo=v.tipo_vinculo,
                detem_guarda=v.detem_guarda,
                principal=v.principal,
            )
        )

    c = dados.consentimento
    db.add(
        Consentimento(
            tenant_id=user.tenant_id,
            paciente_id=paciente.id,
            responsavel_id=c.responsavel_id,
            finalidade_clinica=c.finalidade_clinica,
            limitacoes_acesso=c.limitacoes_acesso,
            termo_versao=c.termo_versao,
            termo_texto=c.termo_texto,
            concedido_por_usuario_id=user.id,
        )
    )
    db.flush()
    # Recarrega com vinculos + responsavel para a resposta detalhada (evita
    # devolver a colecao `vinculos` vazia do objeto recem-criado).
    return obter(db, paciente.id)


def listar(db: Session, *, ativo: bool | None = None) -> list[Paciente]:
    # Sem eager load: a listagem usa PacienteOut (nao inclui vinculos).
    stmt = select(Paciente)
    if ativo is not None:
        stmt = stmt.where(Paciente.ativo.is_(ativo))
    return list(db.execute(stmt.order_by(Paciente.nome)).scalars())


def obter(db: Session, paciente_id: uuid.UUID) -> Paciente | None:
    stmt = (
        select(Paciente)
        .where(Paciente.id == paciente_id)
        .options(
            selectinload(Paciente.vinculos).selectinload(VinculoRespPaciente.responsavel)
        )
    )
    return db.execute(stmt).scalar_one_or_none()


def atualizar(
    db: Session, user: CurrentUser, paciente_id: uuid.UUID, dados: PacienteUpdate
) -> Paciente | None:
    paciente = db.get(Paciente, paciente_id)
    if paciente is None:
        return None
    campos = dados.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(paciente, campo, valor)
    db.flush()
    return paciente


def arquivar(
    db: Session,
    user: CurrentUser,
    paciente_id: uuid.UUID,
    motivo: str | None,
) -> Paciente | None:
    """Arquiva sem apagar; consultas futuras precisam ser resolvidas antes."""
    paciente = db.execute(
        select(Paciente).where(Paciente.id == paciente_id).with_for_update()
    ).scalar_one_or_none()
    if paciente is None:
        return None
    if not paciente.ativo:
        return paciente

    futuras = db.execute(
        select(func.count())
        .select_from(Agendamento)
        .where(
            Agendamento.paciente_id == paciente_id,
            Agendamento.status == STATUS_AGENDADO,
            Agendamento.inicio >= func.now(),
        )
    ).scalar_one()
    if futuras:
        raise PacienteComAgendamentosFuturos(futuras)

    paciente.ativo = False
    paciente.arquivado_em = func.now()
    paciente.arquivado_por_usuario_id = user.id
    paciente.motivo_arquivamento = motivo.strip() if motivo and motivo.strip() else None
    db.flush()

    from app.modules.audit import service as audit_service
    from app.modules.audit.models import TIPO_PACIENTE_ARQUIVADO

    audit_service.registrar_evento(
        db,
        tenant_id=user.tenant_id,
        tipo_evento=TIPO_PACIENTE_ARQUIVADO,
        entidade="paciente",
        entidade_id=paciente.id,
        ator_usuario_id=user.id,
        payload={"motivo_informado": bool(paciente.motivo_arquivamento)},
    )
    return paciente


def reativar(db: Session, user: CurrentUser, paciente_id: uuid.UUID) -> Paciente | None:
    paciente = db.get(Paciente, paciente_id)
    if paciente is None:
        return None
    if paciente.ativo:
        return paciente

    paciente.ativo = True
    paciente.arquivado_em = None
    paciente.arquivado_por_usuario_id = None
    paciente.motivo_arquivamento = None
    db.flush()

    from app.modules.audit import service as audit_service
    from app.modules.audit.models import TIPO_PACIENTE_REATIVADO

    audit_service.registrar_evento(
        db,
        tenant_id=user.tenant_id,
        tipo_evento=TIPO_PACIENTE_REATIVADO,
        entidade="paciente",
        entidade_id=paciente.id,
        ator_usuario_id=user.id,
    )
    return paciente


def apagar_paciente(db: Session, user: CurrentUser, paciente_id: uuid.UUID) -> bool:
    """Exclusao definitiva (Fase 7e) — SO para cadastro errado, sem prontuario.

    Com evolucoes registradas -> `PacienteComProntuario` (409): a guarda de
    prontuario por >=5 anos (CFP 001/2009, §0.3) impede a exclusao; o caminho e
    ARQUIVAR. Defesa em profundidade: o role da app nem tem GRANT DELETE em
    `evolucoes` (migration 0007) — a regra vive no MOTOR (§2.1.1), este check
    so a antecipa com mensagem clara.

    Apaga, na MESMA transacao: agendamentos, consentimentos, vinculos e o
    paciente; grava evento indelevel na auditoria (§2.2). Tudo sob RLS.
    """
    paciente = db.get(Paciente, paciente_id)
    if paciente is None:
        return False
    tem_evolucoes = db.execute(
        select(func.count()).select_from(Evolucao).where(Evolucao.paciente_id == paciente_id)
    ).scalar_one()
    if tem_evolucoes:
        raise PacienteComProntuario(str(paciente_id))

    from app.modules.audit import service as audit_service
    from app.modules.audit.models import TIPO_PACIENTE_APAGADO

    audit_service.registrar_evento(
        db,
        tenant_id=user.tenant_id,
        tipo_evento=TIPO_PACIENTE_APAGADO,
        entidade="paciente",
        entidade_id=paciente.id,
        ator_usuario_id=user.id,
        payload={"nome": paciente.nome, "data_nascimento": paciente.data_nascimento.isoformat()},
    )
    # Ordem respeita os FKs RESTRICT (filhos antes do pai).
    db.execute(delete(Agendamento).where(Agendamento.paciente_id == paciente_id))
    db.execute(delete(Consentimento).where(Consentimento.paciente_id == paciente_id))
    db.execute(delete(VinculoRespPaciente).where(VinculoRespPaciente.paciente_id == paciente_id))
    db.delete(paciente)
    db.flush()
    return True
