#!/bin/sh
# =============================================================================
# 02-roles.sh — executado UMA vez, na inicializacao do volume (primeira subida).
# Provisiona o role de APLICACAO 'agenda_app' (NOSUPERUSER), sujeito ao RLS (§2.1.1).
#
# O dono/superusuario (POSTGRES_USER=agenda_admin) e criado pela propria imagem.
# As tabelas, politicas RLS e grants sao responsabilidade das migrations (Alembic).
#
# Requer no ambiente do contentor: APP_DB_USER, APP_DB_PASSWORD (ver docker-compose).
# =============================================================================
set -e

if [ -z "$APP_DB_PASSWORD" ]; then
  echo "ERRO: APP_DB_PASSWORD nao definido — nao e possivel criar o role de app." >&2
  exit 1
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${APP_DB_USER}') THEN
            CREATE ROLE ${APP_DB_USER}
                LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS
                PASSWORD '${APP_DB_PASSWORD}';
        END IF;
    END
    \$\$;

    GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${APP_DB_USER};
    GRANT USAGE ON SCHEMA public TO ${APP_DB_USER};
EOSQL

echo "Role de aplicacao '${APP_DB_USER}' provisionado (NOSUPERUSER, NOBYPASSRLS)."
