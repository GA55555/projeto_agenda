"""Excecoes da integracao LLM (Fase 6, §2.3/§3.4).

Regras de ouro: §2.3, §3.4
Fase do roadmap: Fase 6
"""


class GeracaoIndisponivel(Exception):
    """Falha ao chamar a OpenAI (sem chave, rede, quota, timeout)."""


class PacienteInexistente(Exception):
    """`paciente_id` nao existe no tenant ativo (RLS)."""
