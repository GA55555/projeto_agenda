"""Excecoes especificas do dominio de consentimentos.

Regras de ouro: §2.2
Fase do roadmap: Fase 3
"""


class ConsentimentoJaRevogado(Exception):
    """Tentativa de revogar um TCLE que ja estava revogado (§2.2)."""
