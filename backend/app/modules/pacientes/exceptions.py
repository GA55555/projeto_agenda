"""Excecoes especificas do dominio de pacientes.

Regras de ouro: §2.2
Fase do roadmap: Fase 3
"""


class ResponsavelInexistente(Exception):
    """Um `responsavel_id` do payload nao existe no tenant ativo (§2.2)."""


class PacienteComProntuario(Exception):
    """Paciente tem evolucoes registradas: exclusao BLOQUEADA (Fase 7e).

    A guarda de prontuario por >=5 anos (CFP 001/2009, §0.3) impede apagar
    registros clinicos; o caminho correto e o ARQUIVAMENTO (ativo=false).
    """
