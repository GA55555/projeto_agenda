"""Reconhecedores por Regex ANCORADO para PII de texto livre (§2.3).

Camada barata e deterministica: pega PII que a psicologa digita no corpo da
nota e que NAO esta cadastrada (um CPF, um telefone, um e-mail, um CEP). Roda
sempre — nao depende de spaCy/Presidio.

Anti-backtracking (§2.3): todos os padroes usam classes de caractere fixas com
quantificadores limitados (`{n}`) e nao ha grupos aninhados com `+`/`*`
sobrepostos — nao ha *catastrophic backtracking* possivel. Cada padrao casa em
tempo linear no tamanho da entrada.

Regras de ouro: §2.3
Fase do roadmap: Fase 4
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.modules.anonimizacao.automaton import Ocorrencia

# Categorias dos marcadores (prefixo do token artificial).
CAT_CPF = "CPF"
CAT_PHONE = "PHONE"
CAT_EMAIL = "EMAIL"
CAT_CEP = "CEP"


@dataclass(frozen=True)
class _Reconhecedor:
    categoria: str
    padrao: re.Pattern[str]


# CPF: 000.000.000-00 ou 00000000000 (11 digitos). Delimitado por nao-digito.
_CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")

# Telefone BR: (00) 90000-0000, 00 90000 0000, +55..., 8-9 digitos com DDD opc.
_PHONE = re.compile(
    r"(?<!\d)(?:\+?55[\s-]?)?(?:\(?\d{2}\)?[\s-]?)?\d{4,5}[\s-]?\d{4}(?!\d)"
)

# E-mail: classes fixas, sem aninhamento ambiguo.
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# CEP: 00000-000 ou 00000000.
_CEP = re.compile(r"(?<!\d)\d{5}-?\d{3}(?!\d)")

# Ordem importa: CPF e CEP antes de PHONE evita que um CPF/CEP seja lido como
# telefone. A resolucao final de sobreposicao (mais longo vence) esta no
# pseudonimizador, mas priorizar aqui reduz ambiguidade.
_RECONHECEDORES: tuple[_Reconhecedor, ...] = (
    _Reconhecedor(CAT_EMAIL, _EMAIL),
    _Reconhecedor(CAT_CPF, _CPF),
    _Reconhecedor(CAT_CEP, _CEP),
    _Reconhecedor(CAT_PHONE, _PHONE),
)


def detectar_por_regex(texto: str) -> list[Ocorrencia]:
    """Todas as ocorrencias de PII estruturada (CPF, telefone, e-mail, CEP)."""
    ocorrencias: list[Ocorrencia] = []
    for rec in _RECONHECEDORES:
        for m in rec.padrao.finditer(texto):
            ocorrencias.append(Ocorrencia(m.start(), m.end(), rec.categoria))
    return ocorrencias
