"""Rotas de autenticacao.

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 2
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.deps import get_db
from app.modules.auth import service
from app.modules.auth.dependencies import CurrentUser, get_current_user
from app.modules.auth.schemas import TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Fluxo OAuth2 password: `username` = email da psicologa, `password` = senha."""
    usuario = service.autenticar(db, form.username, form.password)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        user_id=usuario.id, tenant_id=usuario.tenant_id, papel=usuario.papel
    )
    return TokenResponse(access_token=token)


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)) -> dict[str, str]:
    """Devolve o contexto do JWT (id, tenant, papel) — sem ida a BD."""
    return {"id": str(user.id), "tenant_id": str(user.tenant_id), "papel": user.papel}
