"""Excecoes do pipeline de pseudonimizacao (tunel opaco, §2.3).

Regras de ouro: §2.3
Fase do roadmap: Fase 4
"""


class PIIVazadaError(Exception):
    """Guard-rail de saida: PII conhecida escapou rumo ao LLM (§2.3).

    A Fase 6 usa isto para ABORTAR a chamada externa antes de qualquer byte
    de PII deixar o processo. `termos` lista os trechos que vazaram (para log
    tecnico interno — nunca enviado para fora).
    """

    def __init__(self, termos: list[str]) -> None:
        self.termos = termos
        super().__init__(
            f"PII conhecida detectada no payload de saida ({len(termos)} termo(s))"
        )
