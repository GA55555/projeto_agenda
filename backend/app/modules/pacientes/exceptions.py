"""Excecoes especificas do dominio de pacientes.

Regras de ouro: §2.2
Fase do roadmap: Fase 3
"""


class ResponsavelInexistente(Exception):
    """Um `responsavel_id` do payload nao existe no tenant ativo (§2.2)."""
