"""Regras de negocio de autenticacao.

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 2
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.modules.auth.models import Usuario


def autenticar(db: Session, email: str, senha: str) -> Usuario | None:
    """Retorna o usuario se email+senha conferem e a conta esta ativa; senao None.

    Comparacao de senha sempre executada quando o usuario existe, para reduzir
    o sinal de tempo (nao e defesa forte, mas evita o vazamento obvio).
    """
    usuario = db.execute(
        select(Usuario).where(Usuario.email == email, Usuario.ativo.is_(True))
    ).scalar_one_or_none()
    if usuario is None:
        return None
    if not verify_password(senha, usuario.senha_hash):
        return None
    return usuario
