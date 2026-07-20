"""Excecoes do dominio de evolucoes (§2.2/§3.4).

Regras de ouro: §2.2, §3.4
Fase do roadmap: Fase 5
"""


class PacienteInexistente(Exception):
    """`paciente_id` nao existe no tenant ativo (RLS)."""


class EmbeddingIndisponivel(Exception):
    """Falha ao gerar embedding (sem chave, rede, quota). Nota persiste sem vetor."""


class AgendamentoInvalido(Exception):
    """Agendamento inexistente no tenant, de outro paciente ou nao-realizado (Fase 7e)."""
