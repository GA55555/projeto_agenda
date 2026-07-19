"""Excecoes especificas do dominio de agendamentos.

Regras de ouro: §2.1
Fase do roadmap: Fase 3.5
"""


class PacienteInexistente(Exception):
    """`paciente_id` nao existe no tenant ativo (§2.1)."""


class HorarioIndisponivel(Exception):
    """Sobreposicao com outro atendimento nao-cancelado (EXCLUDE, §2.1)."""


class IntervaloInvalido(Exception):
    """Apos aplicar a atualizacao, `fim <= inicio` (violaria o CHECK do BD)."""
