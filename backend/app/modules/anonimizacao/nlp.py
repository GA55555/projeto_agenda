"""Camada NER (Presidio + spaCy) — REFORCO opcional e lazy (§2.3/§1.3).

Detecta PII NAO cadastrada e nao-estruturada — sobretudo nomes de pessoas e
locais que aparecem no texto livre mas nao estao nas tabelas (ex.: nome de uma
escola, de um colega). E a ultima camada de rede: termos cadastrados
(Aho-Corasick) + regex (CPF/telefone/e-mail/CEP) fazem o trabalho pesado.

Restricoes das Regras de Ouro:
  - §1.3: `presidio_analyzer`/`spacy` sao pesados -> import LAZY, dentro da
    funcao, nunca no escopo do modulo. So carregam quando o NER e realmente
    usado, e apenas se o extra `[nlp]` estiver instalado.
  - §1.1: modelo PEQUENO (`pt_core_news_sm`, ~15 MB) para caber no backend de
    1 GB. Configuravel via `settings.ner_modelo_spacy`.

Degradacao graciosa: se o extra nao estiver instalado, `detectar_por_ner`
devolve lista vazia (as camadas cadastrado+regex seguem valendo) — o pipeline
nunca quebra por falta da dependencia opcional.

Regras de ouro: §2.3, §1.3, §1.1
Fase do roadmap: Fase 4
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.modules.anonimizacao.automaton import Ocorrencia

# Mapa das entidades do Presidio -> categorias dos nossos marcadores.
_MAPA_ENTIDADES: dict[str, str] = {
    "PERSON": "PERSON",
    "LOCATION": "LOCATION",
}


@lru_cache(maxsize=1)
def _analyzer():
    """Carrega o AnalyzerEngine do Presidio UMA vez (import lazy §1.3).

    Cacheado no processo: o custo de subir spaCy paga-se so na 1a chamada.
    Retorna None se o extra `[nlp]` nao estiver instalado.
    """
    try:
        # Imports pesados DENTRO da funcao (§1.3) — nunca no topo do modulo.
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
    except ImportError:
        return None

    # Mapeamento EXPLICITO dos rotulos do modelo pt (PER/LOC/GPE/ORG) para as
    # entidades do Presidio. Sem isto, dependeriamos do default da versao do
    # Presidio — se ele mudar, `analyze()` retornaria vazio e a camada NER
    # viraria no-op SILENCIOSO (PII nao cadastrada vazaria, §2.3).
    config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "pt", "model_name": settings.ner_modelo_spacy}],
        "ner_model_configuration": {
            "model_to_presidio_entity_mapping": {
                "PER": "PERSON",
                "PERSON": "PERSON",
                "LOC": "LOCATION",
                "GPE": "LOCATION",
                "LOCATION": "LOCATION",
            },
            "labels_to_ignore": ["MISC", "ORG"],
        },
    }
    engine = NlpEngineProvider(nlp_configuration=config).create_engine()
    return AnalyzerEngine(nlp_engine=engine, supported_languages=["pt"])


def ner_disponivel() -> bool:
    """True se a camada NER pode operar (flag ligada + extra instalado)."""
    return settings.ner_habilitado and _analyzer() is not None


def detectar_por_ner(texto: str) -> list[Ocorrencia]:
    """Ocorrencias de PERSON/LOCATION detectadas por NER. [] se indisponivel."""
    if not settings.ner_habilitado:
        return []
    analyzer = _analyzer()
    if analyzer is None:
        return []
    resultados = analyzer.analyze(
        text=texto,
        language="pt",
        entities=list(_MAPA_ENTIDADES.keys()),
    )
    ocorrencias: list[Ocorrencia] = []
    for r in resultados:
        categoria = _MAPA_ENTIDADES.get(r.entity_type)
        if categoria is None:
            continue
        ocorrencias.append(Ocorrencia(r.start, r.end, categoria))
    return ocorrencias
