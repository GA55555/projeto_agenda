# Planejamento & Roadmap do Projeto

> **Mapa executável do projeto.** Este documento é o guia de realização e a **memória viva da sessão**. Ele deriva integralmente de [`arquitetura.md`](./arquitetura.md) — em caso de dúvida técnica, a arquitetura manda.
>
> **Como usar este arquivo:**
> - Trabalhe **uma fase de cada vez**. Não abra várias fases em paralelo — a divisão existe para não encher a janela de contexto.
> - Ao concluir uma tarefa, marque `[x]` e adicione uma linha no **Registro de Progresso**.
> - Ao (re)iniciar uma sessão, leia primeiro o **Estado Atual** e o **Registro de Progresso**; só depois entre na fase corrente.
> - Cada fase tem **Objetivo**, **Tarefas**, **Regras de ouro aplicáveis** e **Critério de conclusão (Definition of Done)**.

---

## 📍 Estado Atual da Sessão

| Campo | Valor |
| --- | --- |
| Fase corrente | **Fase 0 — Fundações** |
| Última atualização | 2026-07-17 |
| Bloqueios ativos | Nenhum |
| Próximo passo imediato | Validar `docker compose up` no servidor Debian (criar `.env`); depois iniciar Fase 1 (Alembic, roles, RLS + `FORCE`) |

> Atualize esta tabela ao fim de cada sessão de trabalho.

---

## 🗺️ Visão Geral das Fases

| # | Fase | Objetivo central | Status |
| --- | --- | --- | --- |
| 0 | Fundações & Infra Base | Esqueleto do repositório, Docker e limites de RAM | 🟡 Em progresso (validar no servidor) |
| 1 | Base de Dados & Multitenancy | PostgreSQL + pgvector + RLS funcionando | ⬜ Não iniciado |
| 2 | Backend Core (FastAPI) | API base, auth, injeção de tenant | ⬜ Não iniciado |
| 3 | Modelo de Domínio & Consentimento | Pacientes, responsáveis, TCLE, auditoria | ⬜ Não iniciado |
| 4 | Pipeline de Pseudonimização | Túnel opaco anonimizar/desanonimizar (Aho-Corasick) | ⬜ Não iniciado |
| 5 | IA Vetorial & RAG | Embeddings, filtragem híbrida, chunking | ⬜ Não iniciado |
| 6 | Integração LLM (OpenAI) | Geração de evoluções via túnel de pseudonimização | ⬜ Não iniciado |
| 7 | Frontend (SPA) | Interface das psicólogas, aprovação de evoluções | ⬜ Não iniciado |
| 8 | Automação n8n & Backups | Webhooks, OAuth2, PDFs, pg_dump/WAL | ⬜ Não iniciado |
| 9 | Hardening & Go-Live | Segurança final, limites, observabilidade, deploy | ⬜ Não iniciado |

Legenda: ⬜ Não iniciado · 🟡 Em progresso · ✅ Concluído · ⛔ Bloqueado

---

## Fase 0 — Fundações & Infraestrutura Base

**Objetivo:** repositório versionado, esqueleto de serviços em Docker e limites de RAM aplicados desde o primeiro contentor.

**Regras de ouro aplicáveis:** §1.1 (hard limits), §4.1 (multi-stage, segredos).

### Tarefas
- [x] `git init` e `.gitignore` (ignorar `.env`, `__pycache__`, `node_modules`, dumps). Remote: `github.com/GA55555/projeto_agenda`.
- [x] Estrutura de pastas: `backend/`, `frontend/`, `infra/`, `docs/`.
- [x] Mover `arquitetura.md` e `planejamento_arquitetura.md` para `docs/`.
- [x] `docker-compose.yml` base (postgres + backend, `mem_limit` explícito §1.1). Frontend comentado como TODO da Fase 7.
- [x] **Sem contentor de administração** (pgAdmin/CloudBeaver): admin da BD por `psql` via `docker compose exec` (decisão de menor exposição, §2.1.1/§4.1).
- [x] `.env.example` documentando todas as variáveis (sem valores reais).
- [ ] Configurar Docker Secrets ou `.env` com permissões restritas ao admin.
- [x] `README.md` de bootstrap (como subir o ambiente local).

### Definition of Done
- `docker compose up` sobe os 3 contentores (postgres, backend, frontend) sem exceder o orçamento de RAM.
- Nenhum segredo commitado; `.env` está no `.gitignore`.

---

## Fase 1 — Base de Dados & Multitenancy (RLS)

**Objetivo:** PostgreSQL afinado, pgvector instalado e isolamento por RLS provado com teste.

**Regras de ouro aplicáveis:** §1.1 (1.5 GB), §1.2 (postgresql.conf), §2.1 (RLS), §3.1 (sem índice vetorial).

### Tarefas
- [x] Imagem Postgres com extensão `pgvector` (`CREATE EXTENSION vector`). *(adiantado na Fase 0: imagem `pgvector/pgvector:pg16` + `infra/postgres/init/01-extensions.sql`)*
- [x] `postgresql.conf` afinado: `shared_buffers` 512MB, `work_mem` 8MB, `maintenance_work_mem` 128MB, `max_connections` 50 (§1.2). *(adiantado na Fase 0: `infra/postgres/postgresql.conf`)*
- [ ] Ferramenta de migrations (Alembic).
- [ ] Migration inicial: tabela `tenants` (clínicas/psicólogas) com `id UUID`.
- [ ] Toda tabela clínica nasce com coluna `tenant_id UUID NOT NULL`.
- [ ] **Dois roles distintos:** role de migração (dono das tabelas) × role de app (`agenda_app`, **sem** superusuário/ownership) — pré-requisito para o RLS atuar sobre a aplicação (§2.1.1).
- [ ] Ativar RLS + política `isolamento_tenant` usando `current_setting('app.current_tenant_id')::uuid` (§2.1).
- [ ] **`FORCE ROW LEVEL SECURITY`** nas tabelas clínicas, para que nem o dono escape à política (§2.1.1).
- [ ] Índices B-Tree sobre `tenant_id` e `paciente_id` (pré-filtragem, §3.2).
- [ ] **Teste de isolamento:** dois tenants; provar (ligado como `agenda_app`, não superusuário) que um não vê os dados do outro nem com `SELECT *` genérico. Documentar que o superusuário/`psql` ignora o RLS por desenho (§2.1.1).

### Definition of Done
- Teste automatizado de *cross-tenant leakage* passa (retorno vazio para tenant errado).
- **Nenhum** índice vetorial criado (Pesquisa Exata, §3.1).

---

## Fase 2 — Backend Core (FastAPI)

**Objetivo:** API base com autenticação e injeção automática do contexto de tenant por transação.

**Regras de ouro aplicáveis:** §1.3 (lazy loading, 2 workers, uvloop, GC), §2.1 (`SET LOCAL`), §4.1 (JWT via secrets).

### Tarefas
- [ ] Estrutura FastAPI + SQLAlchemy + pool de ligações dimensionado para `max_connections=50`.
- [ ] Dockerfile **multi-stage** `slim`; entrypoint `uvicorn --workers 2 --loop uvloop` (§1.3).
- [ ] `gc.set_threshold(700, 10, 10)` no arranque (§1.3).
- [ ] Autenticação (JWT), login das psicólogas.
- [ ] **Dependência/middleware que executa `SET LOCAL app.current_tenant_id` dentro da transação** de cada request autenticado (§2.1).
- [ ] Convenção de imports: bibliotecas pesadas (Presidio, spaCy) **só dentro das funções** (§1.3).
- [ ] Healthcheck endpoint.

### Definition of Done
- Request autenticado só enxerga dados do seu tenant (RLS + `SET LOCAL` validados juntos).
- Backend arranca com ≤ 2 workers e respeita `mem_limit` de 1 GB.

---

## Fase 3 — Modelo de Domínio & Consentimento

**Objetivo:** modelar pacientes (menores), responsáveis legais, consentimento e auditoria imutável.

**Regras de ouro aplicáveis:** §2.2 (ECA/LGPD Art. 14, TCLE, auditoria indelével).

### Tarefas
- [ ] Tabela `responsaveis_legais` (perfil detalhado).
- [ ] Tabela `pacientes` **sempre** vinculada a um responsável legal.
- [ ] Tabela `consentimentos` (TCLE): finalidade clínica específica, limitações de acesso, data, responsável.
- [ ] Distinção de acesso: conteúdo terapêutico (sigilo da criança) × informações gerais (acesso dos pais).
- [ ] Tabela de **auditoria imutável** (append-only) para: revogação de consentimento e alteração de guarda legal.
- [ ] Endpoints CRUD respeitando RLS.
- [ ] Agendamentos (agenda de atendimentos) vinculados a paciente + tenant.

### Definition of Done
- Impossível criar paciente sem responsável legal e sem TCLE registrado.
- Revogações/alterações ficam em log inalterável e auditável.

---

## Fase 4 — Pipeline de Pseudonimização (Túnel Opaco)

**Objetivo:** anonimização/desanonimização local, síncrona e reversível — pré-requisito para qualquer chamada ao LLM.

**Regras de ouro aplicáveis:** §2.3 (Aho-Corasick, dicionário volátil, nunca persistir PII).

### Tarefas
- [ ] Motor de deteção com **Aho-Corasick** + Regex otimizado; Presidio como reforço, importado lazy (§1.3/§2.3).
- [ ] Fonte de entidades PII do paciente (nome, familiares, clínica, locais) para alimentar o autômato.
- [ ] `Anonymizer`: mapeia PII → marcadores sequenciais (`<PERSON_1>`, `<LOCATION_1>`).
- [ ] **Dicionário de equivalência em memória volátil**, atrelado à sessão — **jamais gravado na BD** (§2.3).
- [ ] `Deanonymizer`: restaura marcadores no texto de resposta.
- [ ] Testes: round-trip (anonimizar → desanonimizar) preserva o texto; nenhum PII escapa; nenhum dicionário persiste.

### Definition of Done
- Teste prova que texto enviado "para fora" não contém PII.
- Teste prova que o dicionário não é persistido em lugar nenhum.

---

## Fase 5 — IA Vetorial & RAG (pgvector)

**Objetivo:** memória longitudinal do paciente via embeddings, com filtragem híbrida e chunking.

**Regras de ouro aplicáveis:** §3.1 (sem índice), §3.2 (filtragem híbrida obrigatória), §3.3 (chunking).

### Tarefas
- [ ] Tabela `evolucoes` com coluna `embedding vector(1536)` (text-embedding-3-small).
- [ ] Estratégia de **chunking**: particionar relatórios longos em blocos lógicos antes de vetorizar.
- [ ] Serviço de embeddings (geração via OpenAI — texto **já anonimizado** na Fase 4).
- [ ] Consulta RAG **sempre** pré-filtrada por `tenant_id` + `paciente_id`, depois `ORDER BY embedding <=> $vetor LIMIT k` (§3.2).
- [ ] **Confirmar ausência de índice vetorial** (Pesquisa Exata, §3.1).
- [ ] Testes de recall/latência com dados sintéticos.

### Definition of Done
- Query RAG nunca roda sem os filtros de tenant/paciente.
- Latência da busca exata < 50 ms no volume esperado.

---

## Fase 6 — Integração LLM (OpenAI)

**Objetivo:** gerar resumos/evoluções clínicas passando **exclusivamente** por texto anonimizado.

**Regras de ouro aplicáveis:** §2.3 (só texto mascarado sai), §3.3 (prompt dinâmico com contexto recuperado).

### Tarefas
- [ ] Montagem de prompt dinâmico: nota do dia + blocos históricos relevantes (Fase 5), **todos anonimizados**.
- [ ] Chamada à OpenAI recebendo apenas tokens artificiais.
- [ ] Desanonimização da resposta antes de exibir (Fase 4).
- [ ] **Guard-rail:** validação que aborta a chamada se PII for detectada no payload de saída.
- [ ] Tratamento de erros/limites de tokens.
- [ ] Chave OpenAI via Docker Secret / `.env` restrito (§4.1).

### Definition of Done
- Log/inspeção confirma que o payload enviado à OpenAI não tem PII.
- Resposta final ao usuário aparece desanonimizada e legível.

---

## Fase 7 — Frontend (SPA)

**Objetivo:** interface das psicólogas para agenda, prontuários e **aprovação** de evoluções geradas.

**Regras de ouro aplicáveis:** §1.1 (Nginx 100 MB), §2.2 (separação de acessos).

### Tarefas
- [ ] SPA (React ou Vue) — **decidir framework** e registrar no Registro de Progresso.
- [ ] Build servido por Nginx em contentor com `mem_limit` 100 MB (§1.1).
- [ ] Telas: login, agenda, ficha do paciente, editor de evolução.
- [ ] Fluxo de **aprovação**: psicóloga revisa o texto desanonimizado antes de gravar/assinar.
- [ ] Assinatura eletrônica da evolução.
- [ ] Respeitar distinção de acesso pais × conteúdo terapêutico (§2.2).

### Definition of Done
- Fluxo completo: nota → IA → revisão → aprovação → gravação funciona ponta a ponta.
- Contentor frontend respeita 100 MB.

---

## Fase 8 — Automação n8n & Backups

**Objetivo:** descarregar exportação/documentos para o n8n e garantir redundância local.

**Regras de ouro aplicáveis:** §4.2 (webhook autenticado, OAuth2 no n8n, pg_dump/WAL no HDD).

### Tarefas
- [ ] Webhook FastAPI → n8n disparado **após assinatura eletrônica**, com **token/cabeçalho de autenticação** compartilhado (§4.2).
- [ ] Fluxo n8n: JSON → PDF padronizado / Google Sheets.
- [ ] OAuth2 do Google **inteiramente no n8n** (projeto no Google Cloud Console, consent screen, só Drive API + Docs API). App/BD nunca tocam senhas Google (§4.2).
- [ ] Entrega ao diretório encriptado da psicóloga.
- [ ] Rotina diária: `pg_dump` + arquivamento de **WAL** para o **HDD 500 GB** (§4.2).
- [ ] Teste de restauração de backup.

### Definition of Done
- Evolução assinada chega ao Drive via n8n sem a app tocar em credenciais Google.
- Backup diário verificado e restaurável.

---

## Fase 9 — Hardening & Go-Live

**Objetivo:** fechar segurança, validar limites sob carga e colocar em produção.

**Regras de ouro aplicáveis:** todas — revisão contra o **Checklist §5 da arquitetura**.

### Tarefas
- [ ] Rodar o **Checklist de Conformidade (§5)** ponta a ponta.
- [ ] Teste de carga leve validando os `mem_limit` (sem OOM Killer).
- [ ] Revisão de segredos, permissões de arquivos, exposição de portas (confirmar que **não há console web de administração** e que o acesso privilegiado é só por `psql`/`exec` — §2.1.1/§4.1).
- [ ] Observabilidade mínima (logs, uso de RAM por contentor).
- [ ] Verificação de conformidade LGPD/ECA/CFP (consentimento, sigilo, auditoria).
- [ ] Documentar procedimento de restore e plano de contingência.
- [ ] Deploy no servidor Debian 12.

### Definition of Done
- Checklist §5 100% verde.
- Sistema estável em produção dentro do orçamento de RAM.

---

## 📝 Registro de Progresso (memória da sessão)

> Uma linha por entrega significativa. Formato: `AAAA-MM-DD — [Fase X] descrição curta do que foi feito / decidido`.
> Mantenha conciso — este é o resumo que será lido no início das próximas sessões.

- 2026-07-17 — [Fase 0] Criados `arquitetura.md` (regras de ouro) e `planejamento_arquitetura.md` (este roadmap). Projeto ainda sem `git init`.
- 2026-07-17 — [Fase 0] Docs movidos para `docs/`. Estrutura rígida de diretórios criada: backend por domínio/módulo (`core/`, `db/`, `middleware/`, `api/`, `modules/` × 11 domínios), `frontend/`, `infra/`, `tests/`. Criados `.gitignore`, `.env.example`, `README.md`. **Decisão:** backend organizado por domínio/módulo (não por camada).
- 2026-07-17 — [Fase 0] `git init` (branch `main`), primeiro commit e push para `github.com/GA55555/projeto_agenda`. Falta `docker-compose.yml` (§1.1) + `postgresql.conf` (§1.2) + Dockerfiles para fechar a fase.
- 2026-07-17 — [Fase 0/1] Rota 1: `infra/postgres/postgresql.conf` afinado (§1.2, sem log de statements p/ evitar PII) + `init/01-extensions.sql` (pgvector, sem índice §3.1); backend `pyproject.toml` + `Dockerfile` multi-stage slim (§4.1) + app mínimo runnable (`/health`, GC §1.3); `infra/docker-compose.yml` (postgres 1.5GB + backend 1GB, `mem_limit` §1.1; BD sem porta exposta; backend só no localhost). Validado local: app boota e `/health`→200. Docker não roda neste WSL; `docker compose up` fica p/ o servidor Debian (requer criar `.env`).
- 2026-07-17 — [Docs] Avaliada administração da BD. **Decisão: sem GUI** — acesso por `psql` via `docker compose exec` (menor exposição, §0.3; 0 MB, §1.1). pgAdmin descartado. Mantida a **§2.1.1 (nova regra)**: role de app sem privilégio + `FORCE ROW LEVEL SECURITY`; o superusuário/`psql` ignora o RLS por desenho e é *break-glass*. Docs (§0.2, §1.1, §2.1.1, §4.1, §5) e Fases 0/1/9 reconciliados. Debian já constava.

---

## ⚖️ Decisões em Aberto (a resolver)

- [ ] **Framework do frontend:** React ou Vue.js? (Fase 7)
- [x] **Localização dos docs:** `docs/`. ✔ Resolvido 2026-07-17.
- [x] **Layout do backend:** por domínio/módulo. ✔ Resolvido 2026-07-17.
- [ ] Provedor/modelo de embeddings confirmado como `text-embedding-3-small`? (Fase 5)
- [ ] Estratégia de rotação de segredos (Docker Secrets vs. `.env`). (Fase 0)

*Registre aqui toda decisão arquitetural que fugir do `arquitetura.md` e a justificativa.*
