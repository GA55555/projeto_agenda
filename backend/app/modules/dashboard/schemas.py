"""Schema do resumo do dashboard (visao geral, Fase 7c).

Response model puro: numeros ja agregados no BD. Organizado em 3 blocos —
hoje, este mes (gestao) e pendencias (atencao).

Fase do roadmap: Fase 7c
"""
from pydantic import BaseModel


class ResumoDashboard(BaseModel):
    # ---- Hoje / agora ----
    atendimentos_hoje: int  # nao-cancelados com inicio no dia de hoje (fuso da clinica)
    pacientes_ativos: int
    responsaveis: int

    # ---- Este mes (gestao de recursos) ----
    realizados_mes: int
    faltas_mes: int
    cancelados_mes: int
    # realizados / (realizados + faltas) no mes; None quando nao ha base (sem
    # atendimentos concluidos nem faltas ainda) -> a SPA mostra "—".
    taxa_comparecimento_mes: float | None
    dias_com_atendimento_mes: int  # dias distintos com >=1 atendimento realizado
    evolucoes_mes: int

    # ---- Pendencias / atencao ----
    pacientes_sem_tcle: int  # pacientes ativos sem consentimento vigente (§2.2)
    pacientes_sem_agendamento_futuro: int  # pacientes ativos sem proximo atendimento
    atendimentos_proxima_semana: int  # agendados nos proximos 7 dias
