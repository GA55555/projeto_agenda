"""Settings da aplicacao via pydantic-settings (lidas do ambiente).

Segredos vem do ambiente / Docker Secrets, nunca do codigo (§4.1).
Distingue dois papeis de acesso a BD (§2.1.1):
  - admin/migracao (POSTGRES_*): superusuario, dono das tabelas -> migrations.
  - app runtime (APP_DB_* / DATABASE_URL): agenda_app NOSUPERUSER, sujeito ao RLS.

Regras de ouro: §2.1.1, §4.1
Fase do roadmap: Fase 1/2
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # ---- Postgres: role admin/owner (bootstrap + migrations) ----
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "agenda"
    postgres_user: str = "agenda_admin"
    postgres_password: str = ""

    # ---- Postgres: role de aplicacao (NOSUPERUSER, sujeito ao RLS) ----
    app_db_user: str = "agenda_app"
    app_db_password: str = ""
    database_url: str = ""  # runtime (agenda_app); usado a partir da Fase 2

    # ---- JWT (§2.1/§4.1) ----
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    @property
    def admin_database_url(self) -> str:
        """Ligacao com privilegio para rodar migrations (agenda_admin)."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def app_database_url(self) -> str:
        """Ligacao de runtime do backend (agenda_app, sem privilegio)."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.app_db_user}:{self.app_db_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
