"""Excecoes especificas do dominio de consentimentos.

Regras de ouro: §2.2
Fase do roadmap: Fase 3
"""


class ConsentimentoJaRevogado(Exception):
    """Tentativa de revogar um TCLE que ja estava revogado (§2.2)."""


class SemConsentimentoAtivo(Exception):
    """Paciente sem TCLE ativo — operacao clinica bloqueada (§2.2).

    Fonte unica do erro do gate de consentimento (usado por evolucoes e llm),
    par de `tem_consentimento_ativo`.
    """
