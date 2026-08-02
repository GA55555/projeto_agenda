-- Role mínimo usado exclusivamente pelo nó PostgreSQL do receptor n8n.
-- Execute com psql como administrador, informando a variável role_password:
--   psql -X -v ON_ERROR_STOP=1 -v role_password='...' -f role_webhook.sql
-- O valor nunca deve ser salvo neste arquivo nem no histórico do shell.

\if :{?role_password}
\else
  \echo 'ERRO: informe -v role_password=...'
  \quit 1
\endif

SELECT format(
  'CREATE ROLE agenda_webhook LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION PASSWORD %L',
  :'role_password'
)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agenda_webhook')
\gexec

SELECT format('ALTER ROLE agenda_webhook PASSWORD %L', :'role_password')
\gexec

GRANT CONNECT ON DATABASE :DBNAME TO agenda_webhook;
GRANT USAGE ON SCHEMA public TO agenda_webhook;
GRANT SELECT ON TABLE public.agenda_webhook_eventos TO agenda_webhook;
GRANT EXECUTE ON FUNCTION public.agenda_reivindicar_evento(uuid, char) TO agenda_webhook;
GRANT EXECUTE ON FUNCTION public.agenda_concluir_evento(uuid, char, varchar, char) TO agenda_webhook;
GRANT EXECUTE ON FUNCTION public.agenda_falhar_evento(uuid, char, varchar) TO agenda_webhook;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
ON TABLE public.agenda_webhook_eventos FROM agenda_webhook;
