"""Dependencias de sessao de BD para o FastAPI.

- `get_db`: sessao simples (sem contexto de tenant). Usada por rotas de
  control-plane, como o login (consulta a tabela `usuarios`, sem RLS).
- `get_tenant_session`: abre transacao, injeta o `tenant_id` do JWT via
  `set_current_tenant` (SET LOCAL, §2.1) e entrega a sessao. O SET LOCAL e as
  queries partilham a MESMA transacao — no fim, o contexto expira e nada vaza
  entre requisicoes no pool.

Regras de ouro: §2.1, §2.1.1
Fase do roadmap: Fase 2
"""
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db.rls import set_current_tenant
from app.db.session import SessionLocal
from app.modules.auth.dependencies import CurrentUser, get_current_user
from fastapi import Depends


def get_db() -> Iterator[Session]:
    """Sessao sem contexto de tenant (control-plane; ex.: login)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_tenant_session(
    user: CurrentUser = Depends(get_current_user),
) -> Iterator[Session]:
    """Sessao com o locatario do JWT injetado na transacao (RLS ativo, §2.1)."""
    db = SessionLocal()
    try:
        # db.connection() inicia a transacao; o SET LOCAL vale so para ela.
        set_current_tenant(db.connection(), user.tenant_id)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
