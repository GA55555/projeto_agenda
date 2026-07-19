"""Testes unitarios da Fase 5: chunking, canonicalizacao e embeddings sem chave.

Partes puras (sem BD). O fluxo com BD (gate de TCLE, retrieval, RLS) esta em
tests/integration/test_evolucoes.py (roda no servidor).

Regras de ouro: §3.1, §3.3, §3.4
Fase do roadmap: Fase 5
"""
import pytest

from app.modules.evolucoes.chunking import MAX_CHARS, dividir_em_chunks
from app.modules.evolucoes.embeddings import canonicalizar_marcadores, gerar_embedding
from app.modules.evolucoes.exceptions import EmbeddingIndisponivel


# --------------------------------------------------------------------------- #
# Chunking (§3.3)
# --------------------------------------------------------------------------- #
def test_texto_curto_vira_um_chunk():
    assert dividir_em_chunks("Sessao tranquila. Sem crises.") == ["Sessao tranquila. Sem crises."]


def test_texto_vazio_nao_gera_chunks():
    assert dividir_em_chunks("   \n\n  ") == []


def test_paragrafos_viram_chunks_separados():
    texto = "Primeiro bloco sobre ruido.\n\nSegundo bloco sobre rotina."
    chunks = dividir_em_chunks(texto)
    assert len(chunks) == 2
    assert "ruido" in chunks[0] and "rotina" in chunks[1]


def test_paragrafo_longo_e_subdividido_respeitando_o_limite():
    frase = "O paciente reagiu ao som alto da escola. "
    longo = frase * 60  # bem acima de MAX_CHARS
    chunks = dividir_em_chunks(longo)
    assert len(chunks) > 1
    assert all(len(c) <= MAX_CHARS for c in chunks)


# --------------------------------------------------------------------------- #
# Canonicalizacao de marcadores (§3.4 — reduz ruido do embedding)
# --------------------------------------------------------------------------- #
def test_canonicaliza_remove_numeracao_dos_marcadores():
    assert canonicalizar_marcadores("<PERSON_1> e <PERSON_2> em <LOCATION_1>") == (
        "<PERSON> e <PERSON> em <LOCATION>"
    )


def test_canonicaliza_nao_afeta_texto_comum():
    assert canonicalizar_marcadores("crise por ruido na escola") == "crise por ruido na escola"


# --------------------------------------------------------------------------- #
# Embeddings sem chave -> indisponivel (nota persiste, §3.4/decisao Fase 5)
# --------------------------------------------------------------------------- #
def test_embedding_sem_chave_levanta_indisponivel():
    # Sem OPENAI_API_KEY (default vazio nos testes), o cliente e None e a
    # geracao sinaliza indisponibilidade — o service trata como pendente.
    with pytest.raises(EmbeddingIndisponivel):
        gerar_embedding("<PERSON> teve crise por ruido")
