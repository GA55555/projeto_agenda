"""Schemas do dashboard (visao geral + historico, Fase 7c/7e/7f).

Divididos em DIA e MES (Fase 7f): o dashboard tem dois seletores independentes
(calendario/dia e mes de estatisticas). Buscar cada um por conta evita recomputar
as agregacoes do mes/pacientes a cada clique no calendario.

Regras de ouro: §2.1
Fase do roadmap: Fase 7c/7e/7f
"""
from datetime import date, datetime

from pydantic import BaseModel


class ResumoDia(BaseModel):
    dia: date  # dia selecionado (fuso da clinica); default = hoje
    # Bordas [inicio, fim) do dia como INSTANTES (fuso da clinica): a SPA usa
    # estas p/ buscar a agenda do dia -> tile e lista sempre no mesmo dia-clinica.
    dia_inicio: datetime
    dia_fim: datetime
    atendimentos_dia: int  # nao-cancelados com inicio no dia
    realizados_dia: int
    faltas_dia: int
    cancelados_dia: int


class ResumoMes(BaseModel):
    mes: str    # "YYYY-MM" selecionado; default = mes atual
    desde: str  # "YYYY-MM" da criacao da conta — limite inferior do seletor

    # Estado atual (independe do periodo)
    pacientes_ativos: int
    responsaveis: int

    # Mes selecionado (gestao)
    realizados_mes: int
    faltas_mes: int
    cancelados_mes: int
    taxa_comparecimento_mes: float | None  # realizados/(realizados+faltas); None sem base
    dias_com_atendimento_mes: int
    evolucoes_mes: int

    # Pendencias (sempre relativas a AGORA)
    pacientes_sem_tcle: int
    pacientes_sem_agendamento_futuro: int
    atendimentos_proxima_semana: int
