"""Rotas de geracao via LLM. Sob `get_tenant_session` (RLS ativo, §2.1).

`POST /llm/evolucoes/rascunho`: gera um RASCUNHO de evolucao (nao persiste).
Sem TCLE ativo -> 422 (§2.2). PII escapou no payload -> 422 (guard-rail §3.4,
geracao abortada). OpenAI indisponivel -> 503.

Regras de ouro: §2.3, §3.4
Fase do roadmap: Fase 6
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.anonimizacao.exceptions import PIIVazadaError
from app.modules.auth.dependencies import CurrentUser, get_current_user
from app.modules.llm import service
from app.modules.consentimentos.exceptions import SemConsentimentoAtivo
from app.modules.llm.exceptions import GeracaoIndisponivel, PacienteInexistente
from app.modules.llm.schemas import GerarEvolucaoIn, RascunhoOut

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/evolucoes/rascunho", response_model=RascunhoOut)
def gerar_rascunho_evolucao(
    dados: GerarEvolucaoIn,
    db: Session = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> RascunhoOut:
    try:
        return service.gerar_rascunho(db, user, dados)
    except PacienteInexistente as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Paciente inexistente no tenant: {exc}",
        )
    except SemConsentimentoAtivo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Paciente sem consentimento (TCLE) ativo — geracao bloqueada (§2.2)",
        )
    except PIIVazadaError:
        # Salvaguarda §3.4: PII conhecida escapou o mascaramento -> nada foi
        # enviado a OpenAI. Falha fechada (nao degrada para chamada insegura).
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Geracao abortada: PII detectada no payload (guard-rail §3.4)",
        )
    except GeracaoIndisponivel:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geracao indisponivel (OpenAI). Tente novamente.",
        )
