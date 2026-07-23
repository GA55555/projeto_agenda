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

    # ---- Cookie de sessao da SPA (Fase 7, §2.2/§4.1) ----
    # O JWT vai num cookie HTTPONLY (JS nao le -> resistente a XSS). SameSite
    # strict + mesma origem (Nginx faz proxy de /api) => CSRF contido.
    # `cookie_secure` DEFAULT false: o deploy atual e HTTP; um cookie Secure sob
    # HTTP e descartado pelo browser -> login "nao gruda". §9 (go-live com TLS)
    # DEVE definir COOKIE_SECURE=true.
    cookie_name: str = "agenda_session"
    cookie_secure: bool = False
    cookie_samesite: str = "strict"

    # ---- Fuso horario da clinica (Fase 7c) ----
    # Usado para agregar "hoje"/"mes"/"dias com atendimento" no dashboard: os
    # timestamps sao `timestamptz`, mas o RECORTE por dia/mes precisa do fuso
    # local da clinica (senao "hoje" vira o dia UTC). Sem impacto nos dados.
    app_timezone: str = "America/Sao_Paulo"

    # ---- Pseudonimizacao / NER (§2.3/§1.3) ----
    # Camada NER (Presidio + spaCy) e reforco OPCIONAL sobre termos cadastrados
    # + regex. Import lazy (§1.3); requer o extra `[nlp]` instalado. Modelo
    # PEQUENO (pt_core_news_sm) para caber no mem_limit de 1 GB do backend (§1.1).
    ner_habilitado: bool = True
    ner_modelo_spacy: str = "pt_core_news_sm"

    # ---- OpenAI / embeddings (§3.1/§3.4/§4.1) ----
    # Chave via ambiente/Docker Secret, nunca no codigo. O texto que sai para a
    # OpenAI e SEMPRE anonimizado (§3.4). Modelo text-embedding-3-small = 1536 dims.
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    # Timeout CURTO: os embeddings sao sincronos dentro do request e ha apenas 2
    # workers (§1.3). Uma chamada pendurada nao pode bloquear um worker/conexao
    # do pool pelos ~10 min do default da OpenAI. Estouro -> chunk fica pendente.
    openai_timeout_seconds: float = 20.0

    # ---- OpenAI / geracao (Fase 6, §2.3/§3.4) ----
    # Modelo de chat para o rascunho de evolucao. So texto ANONIMIZADO sai (§2.3);
    # sem tools/function-calling (§3.4). Temperatura baixa p/ consistencia clinica.
    openai_chat_model: str = "gpt-4o-mini"
    openai_chat_temperature: float = 0.3
    # Geracao de texto e mais lenta que embeddings (pode levar dezenas de seg);
    # timeout proprio, MAIOR, para nao dar 503 espurio em geracao normal.
    openai_chat_timeout_seconds: float = 60.0

    # ---- Documentos clinicos privados (Fase 7k) ----
    # Volume persistente acessivel apenas pelo backend; nunca sob a raiz do Nginx.
    documentos_dir: str = "/app/data/documentos"
    documentos_tamanho_max_bytes: int = 20 * 1024 * 1024
    documentos_cota_tenant_bytes: int = 2 * 1024 * 1024 * 1024
    documentos_sanitizacao_timeout_seconds: int = 35

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
