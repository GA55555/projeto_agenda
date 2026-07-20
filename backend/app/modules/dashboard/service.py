"""Agregacoes do resumo do dashboard (Fase 7c/7e — com historico dia/mes).

Todas as consultas correm sob a sessao com RLS (§2.1): o motor ja restringe
cada tabela ao tenant ativo, entao NENHUM `WHERE tenant_id` aparece aqui — uma
omissao seria neutralizada pela policy. Os recortes de dia/mes sao calculados
no fuso da clinica (`settings.app_timezone`) para nao cair no dia UTC.

Historico (7e): `dia` e `mes` sao selecionaveis desde a criacao da conta
(`desde` na resposta = mes do `tenants.criado_em`). Pendencias sao sempre
relativas a AGORA. Sem N+1: agregacoes unicas (COUNT/GROUP BY).

Regras de ouro: §2.1
Fase do roadmap: Fase 7c/7e
"""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.consentimentos.service import clausula_consentimento_ativo
from app.modules.dashboard.schemas import ResumoDia, ResumoMes
from app.modules.pacientes.models import Paciente
from app.modules.tenants.models import Tenant


def janela_do_dia(dia: date, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """[inicio do dia, inicio do dia seguinte) no fuso da clinica (aware)."""
    inicio = datetime(dia.year, dia.month, dia.day, tzinfo=tz)
    return inicio, inicio + timedelta(days=1)


def janela_do_mes(ano: int, mes: int, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """[1o dia do mes, 1o dia do mes seguinte) no fuso da clinica (aware)."""
    inicio = datetime(ano, mes, 1, tzinfo=tz)
    # +32 dias e replace(day=1): rollover correto p/ qualquer duracao de mes.
    prox = (inicio + timedelta(days=32)).replace(day=1)
    return inicio, prox


def parse_mes(valor: str) -> tuple[int, int]:
    """'YYYY-MM' -> (ano, mes). ValueError se invalido (router traduz em 422)."""
    ano_s, _, mes_s = valor.partition("-")
    ano, mes = int(ano_s), int(mes_s)
    if not (1 <= mes <= 12):
        raise ValueError(f"mes invalido: {valor!r}")
    return ano, mes


def _scalar(db: Session, sql: str, **params) -> int:
    return int(db.execute(text(sql), params).scalar_one())


def calendario_do_mes(db: Session, mes: str | None = None) -> dict[str, int]:
    """Mapa {dia -> nº de atendimentos nao-cancelados} do mes (Fase 7f).

    Datas no fuso da clinica. Alimenta o calendario do dashboard (dias com
    consulta ficam coloridos). Aceita meses futuros (agenda a frente).
    """
    tz = ZoneInfo(settings.app_timezone)
    agora = datetime.now(tz)
    ano_mes = parse_mes(mes) if mes else (agora.year, agora.month)
    inicio, fim = janela_do_mes(*ano_mes, tz)
    linhas = db.execute(
        text(
            "SELECT (inicio AT TIME ZONE :tz)::date AS d, count(*) FROM agendamentos "
            "WHERE inicio >= :inicio AND inicio < :fim AND status <> 'cancelado' "
            "GROUP BY d"
        ),
        {"tz": settings.app_timezone, "inicio": inicio, "fim": fim},
    ).all()
    return {d.isoformat(): int(n) for d, n in linhas}


def _por_status(db: Session, inicio: datetime, fim: datetime) -> dict[str, int]:
    """Contagem de agendamentos por status na janela [inicio, fim) — 1 query."""
    linhas = db.execute(
        text(
            "SELECT status, count(*) FROM agendamentos "
            "WHERE inicio >= :inicio AND inicio < :fim GROUP BY status"
        ),
        {"inicio": inicio, "fim": fim},
    ).all()
    return {status: int(n) for status, n in linhas}


def montar_resumo_dia(db: Session, dia: date | None = None) -> ResumoDia:
    """Contadores do DIA selecionado (Fase 7f). Buscado ao mudar o dia/calendario."""
    tz = ZoneInfo(settings.app_timezone)
    dia_sel = dia or datetime.now(tz).date()
    inicio_dia, fim_dia = janela_do_dia(dia_sel, tz)

    dia_status = _por_status(db, inicio_dia, fim_dia)
    cancelados_dia = dia_status.get("cancelado", 0)
    atendimentos_dia = sum(dia_status.values()) - cancelados_dia
    return ResumoDia(
        dia=dia_sel,
        dia_inicio=inicio_dia,
        dia_fim=fim_dia,
        atendimentos_dia=atendimentos_dia,
        realizados_dia=dia_status.get("realizado", 0),
        faltas_dia=dia_status.get("falta", 0),
        cancelados_dia=cancelados_dia,
    )


def montar_resumo_mes(db: Session, mes: str | None = None) -> ResumoMes:
    """Estado atual + estatisticas do MES + pendencias (Fase 7f). Buscado ao
    mudar o mes (nao recomputa a cada clique de dia)."""
    tz = ZoneInfo(settings.app_timezone)
    agora = datetime.now(tz)
    ano_mes = parse_mes(mes) if mes else (agora.year, agora.month)
    inicio_mes, fim_mes = janela_do_mes(*ano_mes, tz)

    # Limite inferior do seletor: mes de criacao da conta (RLS -> so a
    # propria linha de `tenants` e visivel).
    criado_em = db.execute(select(Tenant.criado_em)).scalar_one_or_none()
    desde = criado_em.astimezone(tz).strftime("%Y-%m") if criado_em else agora.strftime("%Y-%m")

    # ---- Estado atual + pendencias de pacientes numa passada so ----
    # 3 contadores sobre `pacientes ativos` (total, sem TCLE vigente, sem
    # agendamento futuro) num unico SELECT com subqueries EXISTS -> evita 3
    # varreduras da tabela. TCLE reusa a FONTE UNICA (clausula_consentimento_ativo)
    # para o contador nunca divergir do gate das evolucoes/LLM.
    sem_ag_futuro_clause = text(
        "NOT EXISTS (SELECT 1 FROM agendamentos a WHERE a.paciente_id = pacientes.id "
        "AND a.status = 'agendado' AND a.inicio > :agora)"
    ).bindparams(agora=agora)
    pac_ativos, sem_tcle, sem_ag_futuro = db.execute(
        select(
            func.count(),
            func.count().filter(~clausula_consentimento_ativo(Paciente.id)),
            func.count().filter(sem_ag_futuro_clause),
        )
        .select_from(Paciente)
        .where(Paciente.ativo.is_(True))
    ).one()
    pacientes_ativos = int(pac_ativos)
    pacientes_sem_tcle = int(sem_tcle)
    pacientes_sem_agendamento_futuro = int(sem_ag_futuro)

    responsaveis = _scalar(db, "SELECT count(*) FROM responsaveis_legais")

    # ---- Mes selecionado (1 GROUP BY + 2 agregacoes) ----
    mes_status = _por_status(db, inicio_mes, fim_mes)
    realizados_mes = mes_status.get("realizado", 0)
    faltas_mes = mes_status.get("falta", 0)
    cancelados_mes = mes_status.get("cancelado", 0)
    base = realizados_mes + faltas_mes
    taxa = round(realizados_mes / base, 4) if base else None

    dias_com_atendimento_mes = _scalar(
        db,
        "SELECT count(DISTINCT (inicio AT TIME ZONE :tz)::date) FROM agendamentos "
        "WHERE status = 'realizado' AND inicio >= :inicio AND inicio < :fim",
        tz=settings.app_timezone,
        inicio=inicio_mes,
        fim=fim_mes,
    )
    evolucoes_mes = _scalar(
        db,
        "SELECT count(*) FROM evolucoes WHERE criado_em >= :inicio AND criado_em < :fim",
        inicio=inicio_mes,
        fim=fim_mes,
    )

    # ---- Pendencias (sempre relativas a AGORA) ----
    # pacientes_sem_tcle / pacientes_sem_agendamento_futuro ja computados acima
    # (mesma passada sobre `pacientes ativos`).
    atendimentos_proxima_semana = _scalar(
        db,
        "SELECT count(*) FROM agendamentos WHERE status = 'agendado' "
        "AND inicio > :agora AND inicio <= :fim",
        agora=agora,
        fim=agora + timedelta(days=7),
    )

    return ResumoMes(
        mes=f"{ano_mes[0]:04d}-{ano_mes[1]:02d}",
        desde=desde,
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
