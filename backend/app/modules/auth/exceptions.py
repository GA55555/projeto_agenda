"""Excecoes especificas do dominio.

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 2 / Fase 7c
"""


class EmailDuplicado(Exception):
    """E-mail ja usado por outra conta (viola UNIQUE global em `usuarios.email`)."""


class SenhaAtualIncorreta(Exception):
    """A senha atual informada na troca de senha nao confere."""
