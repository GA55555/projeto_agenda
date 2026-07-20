"""Rotas de autenticacao.

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 2
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token
from app.db.deps import get_db
from app.modules.auth import service
from app.modules.auth.dependencies import CurrentUser, get_current_user
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import PerfilOut, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookie_sessao(response: Response, token: str) -> None:
    """Grava o JWT num cookie httpOnly (SPA, §2.2/§4.1). SameSite strict = CSRF."""
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        httponly=True,               # JS nao le -> resistente a XSS
        secure=settings.cookie_secure,  # exige HTTPS (COOKIE_SECURE=false em dev/HTTP)
        samesite=settings.cookie_samesite,
        path="/",
    )


@router.post("/login", response_model=TokenResponse)
def login(
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Fluxo OAuth2 password: `username` = email da psicologa, `password` = senha.

    Seta o cookie httpOnly (caminho do browser) E devolve o token no corpo
    (compat. com clientes programaticos/testes). A SPA ignora o corpo e usa so
    o cookie.
    """
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
    _set_cookie_sessao(response, token)
    # Dual-mode INTENCIONAL: cookie httpOnly = caminho do browser (a SPA nunca
    # le o corpo); o token no corpo serve clientes bearer (curl/scripts/testes),
    # que precisam do token para o header Authorization. Nao ha ganho em omiti-lo
    # (XSS nao le o cookie httpOnly de qualquer forma). §9 pode ir cookie-only.
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    """Encerra a sessao removendo o cookie (mesmos atributos do set, p/ o browser
    remover de forma confiavel)."""
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    return {"detail": "sessao encerrada"}


@router.get("/me", response_model=PerfilOut)
def me(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Usuario:
    """Perfil do utilizador logado (id, tenant, papel + nome/e-mail p/ a SPA).

    `usuarios` e control-plane (sem RLS); busca por PK. Se o utilizador do JWT
    nao existir mais (revogado), 401 — o token nao vale mais.
    """
    usuario = db.get(Usuario, user.id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nao autenticado")
    return usuario
