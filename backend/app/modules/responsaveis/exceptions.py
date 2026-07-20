"""Excecoes especificas do dominio de responsaveis.

Regras de ouro: §2.2
Fase do roadmap: Fase 3 / Fase 7c
"""


class CpfDuplicado(Exception):
    """CPF ja cadastrado neste tenant (viola UNIQUE(tenant_id, cpf))."""
