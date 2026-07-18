"""Engine e sessionmaker do runtime.

Liga-se como `agenda_app` (NOSUPERUSER, sujeito ao RLS — §2.1.1), NUNCA como
admin. Pool pequeno: com 2 workers (§1.3), ate ~20 ligacoes no total, folgado
dentro do `max_connections=50` (§1.2).

Regras de ouro: §1.2, §2.1.1
Fase do roadmap: Fase 2
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.app_database_url,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)
