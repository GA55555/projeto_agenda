-- =============================================================================
-- verify_rls.sql — prova de isolamento multitenant (§2.1/§2.1.1) sem pytest.
-- Roda numa unica sessao admin usando SET LOCAL ROLE para "virar" agenda_app
-- (a partir dai o RLS e imposto, pois deixa de ser superusuario/owner).
-- Tudo dentro de uma transacao com ROLLBACK: nao deixa residuo na base.
--
-- Uso (no servidor):
--   docker compose exec -T postgres \
--     psql -v ON_ERROR_STOP=1 -U agenda_admin -d agenda -f - < infra/postgres/checks/verify_rls.sql
-- Sucesso  -> imprime "RLS OK" e sai 0.
-- Falha    -> RAISE EXCEPTION aborta a transacao e sai != 0.
-- =============================================================================
BEGIN;

-- Seed como admin (superusuario ignora RLS por desenho).
INSERT INTO tenants (id, nome, slug) VALUES
    ('00000000-0000-0000-0000-000000000001', 'Clinica T1', 't1'),
    ('00000000-0000-0000-0000-000000000002', 'Clinica T2', 't2');

-- A partir daqui, agir como o role de aplicacao (RLS imposto).
SET LOCAL ROLE agenda_app;

-- 1) Contexto = T1  ->  ve apenas T1.
SELECT set_config('app.current_tenant_id', '00000000-0000-0000-0000-000000000001', true);
DO $$
DECLARE total int; vazou int;
BEGIN
    SELECT count(*) INTO total FROM tenants;
    SELECT count(*) INTO vazou FROM tenants WHERE id <> '00000000-0000-0000-0000-000000000001';
    IF total <> 1 OR vazou <> 0 THEN
        RAISE EXCEPTION 'RLS FALHOU: contexto T1 viu % linha(s), vazamento=%', total, vazou;
    END IF;
END $$;

-- 2) Contexto = T2  ->  ve apenas T2.
SELECT set_config('app.current_tenant_id', '00000000-0000-0000-0000-000000000002', true);
DO $$
DECLARE total int; vazou int;
BEGIN
    SELECT count(*) INTO total FROM tenants;
    SELECT count(*) INTO vazou FROM tenants WHERE id <> '00000000-0000-0000-0000-000000000002';
    IF total <> 1 OR vazou <> 0 THEN
        RAISE EXCEPTION 'RLS FALHOU: contexto T2 viu % linha(s), vazamento=%', total, vazou;
    END IF;
END $$;

-- 3) Fail-closed: sem contexto -> ZERO linhas (nega em vez de vazar).
SELECT set_config('app.current_tenant_id', '', true);
DO $$
DECLARE total int;
BEGIN
    SELECT count(*) INTO total FROM tenants;
    IF total <> 0 THEN
        RAISE EXCEPTION 'RLS FALHOU (fail-closed): sem contexto viu % linha(s), esperado 0', total;
    END IF;
END $$;

RESET ROLE;
SELECT 'RLS OK' AS resultado;

ROLLBACK;
