"""Rotas de evolucoes. Todas sob `get_tenant_session` (RLS ativo, §2.1).

Sem TCLE ativo -> 422 (gate §2.2). Paciente fora do tenant -> 422.
Geracao de resumo pelo LLM NAO entra aqui (Fase 6); a busca RAG e servico interno.

Regras de ouro: §2.1, §2.2, §3.4
Fase do roadmap: Fase 5
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.auth.dependencies import CurrentUser, get_current_user
from app.modules.evolucoes import service
from app.modules.consentimentos.exceptions import SemConsentimentoAtivo
from app.modules.evolucoes.exceptions import AgendamentoInvalido, PacienteInexistente
from app.modules.evolucoes.schemas import EvolucaoCreate, EvolucaoOut

router = APIRouter(prefix="/evolucoes", tags=["evolucoes"])


@router.post("", response_model=EvolucaoOut, status_code=status.HTTP_201_CREATED)
def criar_evolucao(
    dados: EvolucaoCreate,
    db: Session = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> EvolucaoOut:
    try:
        return service.criar_evolucao(db, user, dados)
    except PacienteInexistente as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Paciente inexistente no tenant: {exc}",
        )
    except SemConsentimentoAtivo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Paciente sem consentimento (TCLE) ativo — evolucao bloqueada (§2.2)",
        )
    except AgendamentoInvalido as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Agendamento invalido para a evolucao: {exc}",
        )


@router.get("", response_model=list[EvolucaoOut])
def listar_evolucoes(
    paciente_id: uuid.UUID,
    db: Session = Depends(get_tenant_session),
) -> list[EvolucaoOut]:
    return service.listar_por_paciente(db, paciente_id)


@router.get("/{evolucao_id}", response_model=EvolucaoOut)
def obter_evolucao(
    evolucao_id: uuid.UUID, db: Session = Depends(get_tenant_session)
) -> EvolucaoOut:
    ev = service.obter(db, evolucao_id)
    if ev is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evolucao nao encontrada")
    return ev
