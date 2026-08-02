-- Estado mínimo do receptor Agenda -> n8n (Fase 8b, §4.2).
-- Aplicar no PostgreSQL DEDICADO do n8n, nunca no banco clínico da Agenda.
-- A PK é a barreira persistente contra replay; payload_sha256 impede reutilizar
-- um UUID legítimo com corpo diferente.

BEGIN;

CREATE TABLE IF NOT EXISTS agenda_webhook_eventos (
    evento_id uuid PRIMARY KEY,
    payload_sha256 char(64) NOT NULL,
    recebido_em timestamptz NOT NULL DEFAULT now(),
    estado text NOT NULL DEFAULT 'recebido',
    tentativas integer NOT NULL DEFAULT 0,
    processamento_iniciado_em timestamptz,
    processado_em timestamptz,
    proxima_tentativa_em timestamptz,
    ultimo_erro_codigo varchar(80),
    drive_file_id varchar(255),
    pdf_sha256 char(64),
    CONSTRAINT agenda_webhook_payload_sha256_valido
        CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT agenda_webhook_estado_valido
        CHECK (estado IN ('recebido', 'processando', 'processado', 'falhou')),
    CONSTRAINT agenda_webhook_tentativas_validas CHECK (tentativas >= 0),
    CONSTRAINT agenda_webhook_pdf_sha256_valido
        CHECK (pdf_sha256 IS NULL OR pdf_sha256 ~ '^[0-9a-f]{64}$')
);

-- Atualizacao idempotente para instalacoes que ja possuem a tabela antirreplay.
ALTER TABLE agenda_webhook_eventos
    ADD COLUMN IF NOT EXISTS estado text NOT NULL DEFAULT 'recebido',
    ADD COLUMN IF NOT EXISTS tentativas integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS processamento_iniciado_em timestamptz,
    ADD COLUMN IF NOT EXISTS proxima_tentativa_em timestamptz,
    ADD COLUMN IF NOT EXISTS ultimo_erro_codigo varchar(80),
    ADD COLUMN IF NOT EXISTS drive_file_id varchar(255),
    ADD COLUMN IF NOT EXISTS pdf_sha256 char(64);

UPDATE agenda_webhook_eventos
SET estado = 'processado'
WHERE processado_em IS NOT NULL AND estado = 'recebido';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'agenda_webhook_eventos'::regclass
          AND conname = 'agenda_webhook_estado_valido'
    ) THEN
        ALTER TABLE agenda_webhook_eventos
            ADD CONSTRAINT agenda_webhook_estado_valido
            CHECK (estado IN ('recebido', 'processando', 'processado', 'falhou'));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'agenda_webhook_eventos'::regclass
          AND conname = 'agenda_webhook_tentativas_validas'
    ) THEN
        ALTER TABLE agenda_webhook_eventos
            ADD CONSTRAINT agenda_webhook_tentativas_validas CHECK (tentativas >= 0);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'agenda_webhook_eventos'::regclass
          AND conname = 'agenda_webhook_pdf_sha256_valido'
    ) THEN
        ALTER TABLE agenda_webhook_eventos
            ADD CONSTRAINT agenda_webhook_pdf_sha256_valido
            CHECK (pdf_sha256 IS NULL OR pdf_sha256 ~ '^[0-9a-f]{64}$');
    END IF;
END
$$;

CREATE OR REPLACE FUNCTION agenda_reivindicar_evento(
    p_evento_id uuid,
    p_payload_sha256 char(64)
)
RETURNS TABLE(decisao text, estado text, tentativas integer)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_evento public.agenda_webhook_eventos%ROWTYPE;
BEGIN
    INSERT INTO public.agenda_webhook_eventos (evento_id, payload_sha256)
    VALUES (p_evento_id, p_payload_sha256)
    ON CONFLICT (evento_id) DO NOTHING;

    SELECT * INTO v_evento
    FROM public.agenda_webhook_eventos
    WHERE evento_id = p_evento_id
    FOR UPDATE;

    IF v_evento.payload_sha256 <> p_payload_sha256 THEN
        RETURN QUERY SELECT 'replay_divergente', v_evento.estado, v_evento.tentativas;
        RETURN;
    END IF;

    IF v_evento.estado = 'processado' THEN
        RETURN QUERY SELECT 'ja_processado', v_evento.estado, v_evento.tentativas;
        RETURN;
    END IF;

    IF v_evento.estado = 'processando'
       AND v_evento.processamento_iniciado_em > now() - interval '5 minutes' THEN
        RETURN QUERY SELECT 'em_processamento', v_evento.estado, v_evento.tentativas;
        RETURN;
    END IF;

    IF v_evento.estado = 'falhou'
       AND v_evento.proxima_tentativa_em > now() THEN
        RETURN QUERY SELECT 'aguardar_retry', v_evento.estado, v_evento.tentativas;
        RETURN;
    END IF;

    UPDATE public.agenda_webhook_eventos
    SET estado = 'processando',
        tentativas = agenda_webhook_eventos.tentativas + 1,
        processamento_iniciado_em = now(),
        proxima_tentativa_em = NULL,
        ultimo_erro_codigo = NULL
    WHERE evento_id = p_evento_id
    RETURNING agenda_webhook_eventos.estado, agenda_webhook_eventos.tentativas
    INTO v_evento.estado, v_evento.tentativas;

    RETURN QUERY SELECT 'processar', v_evento.estado, v_evento.tentativas;
END;
$$;

CREATE OR REPLACE FUNCTION agenda_concluir_evento(
    p_evento_id uuid,
    p_payload_sha256 char(64),
    p_drive_file_id varchar(255),
    p_pdf_sha256 char(64)
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    UPDATE public.agenda_webhook_eventos
    SET estado = 'processado',
        processado_em = now(),
        processamento_iniciado_em = NULL,
        proxima_tentativa_em = NULL,
        ultimo_erro_codigo = NULL,
        drive_file_id = p_drive_file_id,
        pdf_sha256 = p_pdf_sha256
    WHERE evento_id = p_evento_id
      AND payload_sha256 = p_payload_sha256
      AND estado = 'processando';
    RETURN FOUND;
END;
$$;

CREATE OR REPLACE FUNCTION agenda_falhar_evento(
    p_evento_id uuid,
    p_payload_sha256 char(64),
    p_erro_codigo varchar(80)
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF p_erro_codigo !~ '^[a-z0-9_:-]{1,80}$' THEN
        RAISE EXCEPTION 'codigo de erro invalido';
    END IF;

    UPDATE public.agenda_webhook_eventos
    SET estado = 'falhou',
        processamento_iniciado_em = NULL,
        proxima_tentativa_em = now() + interval '1 minute',
        ultimo_erro_codigo = p_erro_codigo
    WHERE evento_id = p_evento_id
      AND payload_sha256 = p_payload_sha256
      AND estado = 'processando';
    RETURN FOUND;
END;
$$;

REVOKE ALL ON TABLE agenda_webhook_eventos FROM PUBLIC;
REVOKE ALL ON FUNCTION agenda_reivindicar_evento(uuid, char) FROM PUBLIC;
REVOKE ALL ON FUNCTION agenda_concluir_evento(uuid, char, varchar, char) FROM PUBLIC;
REVOKE ALL ON FUNCTION agenda_falhar_evento(uuid, char, varchar) FROM PUBLIC;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agenda_webhook') THEN
        GRANT SELECT ON TABLE public.agenda_webhook_eventos TO agenda_webhook;
        REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
            ON TABLE public.agenda_webhook_eventos FROM agenda_webhook;
        GRANT EXECUTE ON FUNCTION public.agenda_reivindicar_evento(uuid, char)
            TO agenda_webhook;
        GRANT EXECUTE ON FUNCTION public.agenda_concluir_evento(uuid, char, varchar, char)
            TO agenda_webhook;
        GRANT EXECUTE ON FUNCTION public.agenda_falhar_evento(uuid, char, varchar)
            TO agenda_webhook;
    END IF;
END
$$;

COMMIT;
