"""Hash de senha (bcrypt) e emissao/validacao de JWT.

Usa a lib `bcrypt` diretamente (passlib 1.7 e incompativel com bcrypt >= 4.1).
Segredo do JWT vem das settings (ambiente/secrets, §4.1).

Nota: bcrypt trunca a senha em 72 bytes (comportamento padrao) — irrelevante
para senhas normais.

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 2
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_password(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except ValueError:
        # senha_hash em formato invalido
        return False


def create_access_token(*, user_id, tenant_id, papel: str) -> str:
    """Emite um JWT de acesso com o locatario (psicologa) embutido."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "papel": papel,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Valida assinatura/expiracao e devolve o payload. Levanta jwt.PyJWTError."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
