"""Orquestracao do tunel LLM completo (Fase 6) — onde tudo converge.

Fluxo (§2.3/§3.3/§3.4):
  1. Gate de consentimento (§2.2): paciente PRECISA de TCLE ativo.
  2. Recupera historico relevante via RAG (§3.2, Fase 5) — chunks CRUS.
  3. Monta o bloco de dados (nota do dia + historico) e ANONIMIZA numa unica
     passagem -> marcadores consistentes em todo o prompt (§2.3).
  4. GUARD-RAIL (§3.4 #4): aborta se PII conhecida escapou no payload de saida —
     nenhuma chamada externa acontece.
  5. Chama a OpenAI com instrucao separada do dado, sem tools, retencao-zero (§3.4).
  6. DESANONIMIZA a resposta com o mesmo mapa volatil (§2.3) e devolve o rascunho
     legivel para revisao da psicologa (Fase 7). Nada e persistido (stateless).

Regras de ouro: §2.3, §3.3, §3.4, §2.2
Fase do roadmap: Fase 6
"""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy.orm import Session

from app.modules.anonimizacao import (
    anonimizar_com_entidades,
    desanonimizar_texto,
    entidades_do_paciente,
    verificar_sem_pii,
)
from app.modules.auth.dependencies import CurrentUser
from app.modules.consentimentos.exceptions import SemConsentimentoAtivo
from app.modules.consentimentos.service import tem_consentimento_ativo
from app.modules.evolucoes.service import buscar_contexto
from app.modules.llm.client import gerar_json
from app.modules.llm.exceptions import PacienteInexistente
from app.modules.llm.prompts import SYSTEM_INSTRUCAO, construir_mensagens, montar_bloco_dados
from app.modules.llm.schemas import GerarEvolucaoIn, RascunhoOut
from app.modules.pacientes.models import Paciente

logger = logging.getLogger(__name__)

K_CONTEXTO = 5  # trechos do historico no prompt (§3.2, LIMIT do exemplo)

# Marcador residual que o LLM possa ter inventado (ex.: <PERSON_9> inexistente no
# mapa) e a desanonimizacao nao restaurou. Removido da saida para nao confundir.
_MARCADOR_RESIDUAL = re.compile(r"<[A-Z]+(?:_\d+)?>")


def _limpar_marcadores_residuais(texto: str) -> str:
    """Remove marcadores nao resolvidos e normaliza espacos duplicados."""
    return re.sub(r"\s{2,}", " ", _MARCADOR_RESIDUAL.sub("", texto)).strip()


def gerar_rascunho(db: Session, user: CurrentUser, dados: GerarEvolucaoIn) -> RascunhoOut:
    if db.get(Paciente, dados.paciente_id) is None:
        raise PacienteInexistente(str(dados.paciente_id))
    if not tem_consentimento_ativo(db, dados.paciente_id):
        raise SemConsentimentoAtivo(str(dados.paciente_id))

    entidades = entidades_do_paciente(db, dados.paciente_id)
    contexto = buscar_contexto(
        db, user.tenant_id, dados.paciente_id, dados.nota_do_dia, entidades, k=K_CONTEXTO
    )

    # Monta CRU e anonimiza de uma vez (entidades ja coletadas, sem re-query) ->
    # mesmo nome vira o MESMO marcador na nota e no historico (§2.3).
    bloco_raw = montar_bloco_dados(dados.nota_do_dia, contexto)
    bloco_masc, mapa = anonimizar_com_entidades(entidades, bloco_raw)

    # GUARD-RAIL do payload de saida (instrucao + dado). Aborta ANTES da OpenAI
    # se qualquer PII conhecida escapou (§3.4 #4). Propaga PIIVazadaError.
    verificar_sem_pii(f"{SYSTEM_INSTRUCAO}\n{bloco_masc}", entidades)

    resposta_mascarada = gerar_json(construir_mensagens(bloco_masc))
    evolucao_masc, destaques_masc = _parse_resposta(resposta_mascarada)

    # DESANONIMIZA (§2.3) — restaura nomes reais so na saida para a psicologa;
    # remove marcadores residuais que o LLM porventura tenha inventado (§3.4 #3).
    return RascunhoOut(
        evolucao=_limpar_marcadores_residuais(desanonimizar_texto(evolucao_masc, mapa)),
        destaques=[
            _limpar_marcadores_residuais(desanonimizar_texto(d, mapa)) for d in destaques_masc
        ],
        chunks_contexto=len(contexto),
    )


def _parse_resposta(conteudo_json: str) -> tuple[str, list[str]]:
    """Extrai (evolucao, destaques) do JSON mascarado. Tolerante a formato ruim.

    Faz o parse do JSON AINDA mascarado (limpo) e so depois desanonimiza os
    valores — evita que um nome restaurado com caractere especial corrompa o JSON.
    """
    try:
        dados = json.loads(conteudo_json)
    except (json.JSONDecodeError, TypeError):
        logger.warning("resposta do LLM nao e JSON valido; devolvendo texto cru")
        return conteudo_json.strip(), []
    evolucao = str(dados.get("evolucao", "")).strip()
    brutos = dados.get("destaques", [])
    destaques = [str(d).strip() for d in brutos if str(d).strip()] if isinstance(brutos, list) else []
    return evolucao, destaques
