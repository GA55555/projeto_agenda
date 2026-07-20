"""Agregacoes do resumo do dashboard (Fase 7c).

Todas as consultas correm sob a sessao com RLS (§2.1): o motor ja restringe
cada tabela ao tenant ativo, entao NENHUM `WHERE tenant_id` aparece aqui — uma
omissao seria neutralizada pela policy. Os recortes de "hoje"/"mes" sao
calculados no fuso da clinica (`settings.app_timezone`) para nao cair no dia UTC.

Sem N+1: cada indicador e uma agregacao unica (COUNT/GROUP BY), nunca um laco
por paciente. Volume da clinica (<= 5 profissionais) torna o custo desprezivel.

Regras de ouro: §2.1
Fase do roadmap: Fase 7c
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.consentimentos.service import clausula_consentimento_ativo
from app.modules.dashboard.schemas import ResumoDashboard
from app.modules.pacientes.models import Paciente


def _limites(agora: datetime) -> dict[str, datetime]:
    """Bordas de hoje / amanha / mes / proxima semana, no fuso da clinica.

    Datas *aware*: comparadas contra colunas `timestamptz`, o Postgres resolve
    o fuso corretamente independente de como o instante e representado.
    """
    inicio_hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_mes = inicio_hoje.replace(day=1)
    # 1o dia do mes seguinte sem depender do numero de dias do mes atual.
    inicio_prox_mes = (inicio_mes + timedelta(days=32)).replace(day=1)
    return {
        "inicio_hoje": inicio_hoje,
        "inicio_amanha": inicio_hoje + timedelta(days=1),
        "inicio_mes": inicio_mes,
        "inicio_prox_mes": inicio_prox_mes,
        "daqui_uma_semana": agora + timedelta(days=7),
        "agora": agora,
    }


def _scalar(db: Session, sql: str, **params) -> int:
    return int(db.execute(text(sql), params).scalar_one())


def montar_resumo(db: Session) -> ResumoDashboard:
    tz = ZoneInfo(settings.app_timezone)
    agora = datetime.now(tz)
    lim = _limites(agora)

    atendimentos_hoje = _scalar(
        db,
        "SELECT count(*) FROM agendamentos "
        "WHERE inicio >= :inicio_hoje AND inicio < :inicio_amanha "
        "AND status <> 'cancelado'",
        **lim,
    )
    pacientes_ativos = _scalar(db, "SELECT count(*) FROM pacientes WHERE ativo = true")
    responsaveis = _scalar(db, "SELECT count(*) FROM responsaveis_legais")

    # Um unico GROUP BY resolve os 3 status do mes (sem 3 varreduras).
    por_status = dict(
        db.execute(
            text(
                "SELECT status, count(*) FROM agendamentos "
                "WHERE inicio >= :inicio_mes AND inicio < :inicio_prox_mes "
                "GROUP BY status"
            ),
            {"inicio_mes": lim["inicio_mes"], "inicio_prox_mes": lim["inicio_prox_mes"]},
        ).all()
    )
    realizados_mes = int(por_status.get("realizado", 0))
    faltas_mes = int(por_status.get("falta", 0))
    cancelados_mes = int(por_status.get("cancelado", 0))
    base = realizados_mes + faltas_mes
    taxa = round(realizados_mes / base, 4) if base else None

    dias_com_atendimento_mes = _scalar(
        db,
        "SELECT count(DISTINCT (inicio AT TIME ZONE :tz)::date) FROM agendamentos "
        "WHERE status = 'realizado' AND inicio >= :inicio_mes AND inicio < :inicio_prox_mes",
        tz=settings.app_timezone,
        inicio_mes=lim["inicio_mes"],
        inicio_prox_mes=lim["inicio_prox_mes"],
    )
    evolucoes_mes = _scalar(
        db,
        "SELECT count(*) FROM evolucoes WHERE criado_em >= :inicio_mes AND criado_em < :inicio_prox_mes",
        inicio_mes=lim["inicio_mes"],
        inicio_prox_mes=lim["inicio_prox_mes"],
    )

    # Pendencias: pacientes ativos sem TCLE vigente (§2.2) / sem proximo atendimento.
    # Predicado do TCLE reusa a FONTE UNICA (consentimentos.clausula_consentimento_ativo)
    # para o contador nunca divergir do gate das evolucoes/LLM.
    pacientes_sem_tcle = int(
        db.execute(
            select(func.count())
            .select_from(Paciente)
            .where(Paciente.ativo.is_(True))
            .where(~clausula_consentimento_ativo(Paciente.id))
        ).scalar_one()
    )
    pacientes_sem_agendamento_futuro = _scalar(
        db,
        "SELECT count(*) FROM pacientes p WHERE p.ativo = true AND NOT EXISTS ("
        "  SELECT 1 FROM agendamentos a WHERE a.paciente_id = p.id "
        "  AND a.status = 'agendado' AND a.inicio > :agora)",
        agora=lim["agora"],
    )
    atendimentos_proxima_semana = _scalar(
        db,
        "SELECT count(*) FROM agendamentos WHERE status = 'agendado' "
        "AND inicio > :agora AND inicio <= :daqui_uma_semana",
        agora=lim["agora"],
        daqui_uma_semana=lim["daqui_uma_semana"],
    )

    return ResumoDashboard(
        atendimentos_hoje=atendimentos_hoje,
        pacientes_ativos=pacientes_ativos,
        responsaveis=responsaveis,
        realizados_mes=realizados_mes,
        faltas_mes=faltas_mes,
        cancelados_mes=cancelados_mes,
        taxa_comparecimento_mes=taxa,
        dias_com_atendimento_mes=dias_com_atendimento_mes,
        evolucoes_mes=evolucoes_mes,
        pacientes_sem_tcle=pacientes_sem_tcle,
        pacientes_sem_agendamento_futuro=pacientes_sem_agendamento_futuro,
        atendimentos_proxima_semana=atendimentos_proxima_semana,
    )
