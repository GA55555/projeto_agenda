"""Schema do resumo do dashboard (visao geral + historico, Fase 7c/7e).

Response model puro: numeros ja agregados no BD, para um DIA e um MES
selecionaveis (historico desde a criacao da conta). Pendencias sao sempre
relativas a AGORA (independem do periodo escolhido).

Regras de ouro: §2.1
Fase do roadmap: Fase 7c/7e
"""
from datetime import date, datetime

from pydantic import BaseModel


class ResumoDashboard(BaseModel):
    # ---- Contexto do periodo selecionado ----
    dia: date   # dia selecionado (fuso da clinica); default = hoje
    mes: str    # "YYYY-MM" selecionado; default = mes atual
    desde: str  # "YYYY-MM" da criacao da conta — limite inferior dos seletores
    # Bordas [inicio, fim) do dia como INSTANTES (fuso da clinica): a SPA usa
    # estas p/ buscar a agenda do dia -> tile e lista sempre no mesmo dia-clinica
    # (o browser nao recalcula o dia no fuso local).
    dia_inicio: datetime
    dia_fim: datetime

    # ---- Estado atual (independe do periodo) ----
    pacientes_ativos: int
    responsaveis: int

    # ---- Dia selecionado ----
    atendimentos_dia: int  # nao-cancelados com inicio no dia
    realizados_dia: int
    faltas_dia: int
    cancelados_dia: int

    # ---- Mes selecionado (gestao de recursos) ----
    realizados_mes: int
    faltas_mes: int
    cancelados_mes: int
    # realizados / (realizados + faltas); None sem base -> a SPA mostra "—".
    taxa_comparecimento_mes: float | None
    dias_com_atendimento_mes: int  # dias distintos com >=1 atendimento realizado
    evolucoes_mes: int

    # ---- Pendencias / atencao (sempre "agora") ----
    pacientes_sem_tcle: int  # pacientes ativos sem consentimento vigente (§2.2)
    pacientes_sem_agendamento_futuro: int
    atendimentos_proxima_semana: int
