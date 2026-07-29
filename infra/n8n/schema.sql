-- Estado mínimo do receptor Agenda -> n8n (Fase 8b, §4.2).
-- Aplicar no PostgreSQL DEDICADO do n8n, nunca no banco clínico da Agenda.
-- A PK é a barreira persistente contra replay; payload_sha256 impede reutilizar
-- um UUID legítimo com corpo diferente.

BEGIN;

CREATE TABLE IF NOT EXISTS agenda_webhook_eventos (
    evento_id uuid PRIMARY KEY,
    payload_sha256 char(64) NOT NULL,
    recebido_em timestamptz NOT NULL DEFAULT now(),
    processado_em timestamptz,
    CONSTRAINT agenda_webhook_payload_sha256_valido
        CHECK (payload_sha256 ~ '^[0-9a-f]{64}$')
);

REVOKE ALL ON TABLE agenda_webhook_eventos FROM PUBLIC;

COMMIT;
