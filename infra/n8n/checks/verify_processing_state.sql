\set ON_ERROR_STOP on

DO $$
BEGIN
    IF has_table_privilege('agenda_webhook', 'public.agenda_webhook_eventos', 'INSERT') THEN
        RAISE EXCEPTION 'role operacional ainda possui INSERT direto';
    END IF;
    IF NOT has_function_privilege(
        'agenda_webhook',
        'public.agenda_reivindicar_evento(uuid,character)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'role operacional sem EXECUTE na funcao de claim';
    END IF;
END
$$;

CREATE ROLE agenda_webhook_test NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOLOGIN;
GRANT USAGE ON SCHEMA public TO agenda_webhook_test;
GRANT SELECT ON TABLE public.agenda_webhook_eventos TO agenda_webhook_test;
GRANT EXECUTE ON FUNCTION public.agenda_reivindicar_evento(uuid, char) TO agenda_webhook_test;
GRANT EXECUTE ON FUNCTION public.agenda_concluir_evento(uuid, char, varchar, char) TO agenda_webhook_test;
GRANT EXECUTE ON FUNCTION public.agenda_falhar_evento(uuid, char, varchar) TO agenda_webhook_test;

SET ROLE agenda_webhook_test;

SELECT decisao = 'processar' AND estado = 'processando' AND tentativas = 1 AS claim_novo_ok
FROM agenda_reivindicar_evento(
    '11111111-1111-4111-8111-111111111111',
    repeat('a', 64)::char(64)
);

SELECT decisao = 'em_processamento' AS concorrencia_bloqueada_ok
FROM agenda_reivindicar_evento(
    '11111111-1111-4111-8111-111111111111',
    repeat('a', 64)::char(64)
);

SELECT agenda_concluir_evento(
    '11111111-1111-4111-8111-111111111111',
    repeat('a', 64)::char(64),
    'drive-sintetico-1',
    repeat('b', 64)::char(64)
) AS conclusao_ok;

SELECT decisao = 'ja_processado' AS retry_processado_ok
FROM agenda_reivindicar_evento(
    '11111111-1111-4111-8111-111111111111',
    repeat('a', 64)::char(64)
);

SELECT decisao = 'replay_divergente' AS replay_divergente_ok
FROM agenda_reivindicar_evento(
    '11111111-1111-4111-8111-111111111111',
    repeat('c', 64)::char(64)
);

SELECT decisao = 'processar' AS claim_falha_ok
FROM agenda_reivindicar_evento(
    '22222222-2222-4222-8222-222222222222',
    repeat('d', 64)::char(64)
);

SELECT agenda_falhar_evento(
    '22222222-2222-4222-8222-222222222222',
    repeat('d', 64)::char(64),
    'google_indisponivel'
) AS falha_ok;

SELECT decisao = 'aguardar_retry' AS backoff_ok
FROM agenda_reivindicar_evento(
    '22222222-2222-4222-8222-222222222222',
    repeat('d', 64)::char(64)
);

DO $$
BEGIN
    BEGIN
        UPDATE public.agenda_webhook_eventos SET estado = 'processado';
        RAISE EXCEPTION 'UPDATE direto foi permitido indevidamente';
    EXCEPTION WHEN insufficient_privilege THEN
        NULL;
    END;
END
$$;

RESET ROLE;

DO $$
DECLARE
    v_falhas integer;
BEGIN
    SELECT count(*) INTO v_falhas
    FROM (
        SELECT NOT (estado = 'processado' AND tentativas = 1
                    AND drive_file_id = 'drive-sintetico-1'
                    AND pdf_sha256 = repeat('b', 64)::char(64)) AS falhou
        FROM agenda_webhook_eventos
        WHERE evento_id = '11111111-1111-4111-8111-111111111111'
    ) verificacoes
    WHERE falhou;
    IF v_falhas <> 0 THEN
        RAISE EXCEPTION 'estado final divergente';
    END IF;
END
$$;

REVOKE ALL ON FUNCTION public.agenda_reivindicar_evento(uuid, char) FROM agenda_webhook_test;
REVOKE ALL ON FUNCTION public.agenda_concluir_evento(uuid, char, varchar, char) FROM agenda_webhook_test;
REVOKE ALL ON FUNCTION public.agenda_falhar_evento(uuid, char, varchar) FROM agenda_webhook_test;
REVOKE ALL ON TABLE public.agenda_webhook_eventos FROM agenda_webhook_test;
REVOKE ALL ON SCHEMA public FROM agenda_webhook_test;
DROP ROLE agenda_webhook_test;

\echo 'PROCESSAMENTO DURAVEL OK'
