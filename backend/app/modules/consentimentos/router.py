"""Rotas de consentimentos (TCLE). Todas sob `get_tenant_session` (RLS, §2.1).

O TCLE e criado junto do paciente (POST /pacientes). Aqui: consulta por paciente
e revogacao (que gera registro imutavel em auditoria, §2.2).

Regras de ouro: §2.1, §2.2
Fase do roadmap: Fase 3
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.auth.dependencies import CurrentUser, get_current_user
from app.modules.consentimentos import service
from app.modules.consentimentos.exceptions import ConsentimentoJaRevogado
from app.modules.consentimentos.schemas import ConsentimentoOut, RevogacaoIn

router = APIRouter(prefix="/consentimentos", tags=["consentimentos"])


@router.get("", response_model=list[ConsentimentoOut])
def listar_por_paciente(
    paciente_id: uuid.UUID, db: Session = Depends(get_tenant_session)
) -> list[ConsentimentoOut]:
    return service.listar_por_paciente(db, paciente_id)


@router.post("/{consentimento_id}/revogar", response_model=ConsentimentoOut)
def revogar_consentimento(
    consentimento_id: uuid.UUID,
    dados: RevogacaoIn,
    db: Session = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> ConsentimentoOut:
    try:
        consentimento = service.revogar(db, user, consentimento_id, dados.motivo)
    except ConsentimentoJaRevogado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Consentimento ja revogado"
        )
    if consentimento is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Consentimento nao encontrado"
        )
    return consentimento
