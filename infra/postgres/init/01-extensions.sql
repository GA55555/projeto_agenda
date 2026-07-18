-- =============================================================================
-- 01-extensions.sql — executado UMA vez, na inicializacao do volume (primeira
-- subida do contentor), contra o banco POSTGRES_DB. Base: imagem pgvector.
--
-- Aqui ficam apenas extensoes. Roles (migracao x app), tabelas, RLS e
-- FORCE ROW LEVEL SECURITY sao responsabilidade das migrations (Alembic) na
-- Fase 1 — ver §2.1 / §2.1.1.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector: coluna embedding vector(1536) (§3.1)

-- Nao criar indice vetorial nesta fase — Pesquisa Exata resolve (§3.1).
