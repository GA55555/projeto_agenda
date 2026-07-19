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
| Fase corrente | **Fases 3 e 3.5 ✅ concluídas e validadas no servidor** — próxima: **Fase 4 (Pipeline de Pseudonimização)** |
| Última atualização | 2026-07-19 |
| Bloqueios ativos | Nenhum |
| Próximo passo imediato | Planejar a **Fase 4** (túnel opaco §2.3: Aho-Corasick + Presidio lazy, dicionário volátil) — usuário quer plano detalhado + perguntas de design antes de codar. |

> Atualize esta tabela ao fim de cada sessão de trabalho.

### 🔖 Ponto de Retomada (ler primeiro na próxima sessão)

**Onde paramos (2026-07-19):** Fases **0, 1, 2, 3, 3.5 ✅** concluídas e validadas no servidor. Branch `main` sincronizado (última migration = **`0004`**; servidor em `0004 (head)`). Sem trabalho pendente/não-commitado.

**Próxima ação:** planejar a **Fase 4 (Pipeline de Pseudonimização, §2.3)** — usuário quer **plano detalhado + perguntas de design (AskUserQuestion) ANTES de codar** (ver as perguntas já levantadas na seção da Fase 4). É a peça mais sensível: princípio de **risco zero de PII** (§0.3/§2.3).

**Fluxo de trabalho (imutável):** plano → construir/validar local (WSL, sem Docker: `py_compile` + venv de teste `pytest tests/unit` + render offline do SQL) → **revisar com o usuário** (trazer diff/resumo) → `/code-review` alto esforço → **commit direto em `main`** (Co-Authored-By) → **usuário** faz deploy no servidor (`git pull` → `up -d --build backend` → `alembic upgrade head`) e valida → marcar ✅ aqui. Comandos ao usuário **uma linha por vez** (terminal quebra pastes compostos). Ver [[feedback-fluxo-trabalho-agenda]].

**Contexto de ambiente/dados (servidor, descartáveis):** 1 psicóloga de teste `teste@clinica.local` / `SenhaForte123` (slug `teste`); paciente `316b1a57-…` + responsável `19ebfffa-…` (CPF `11122233344`, TCLE **revogado**); ≥1 agendamento criado (`2026-08-01` 14–16h). Módulos ainda **stub/vazios**: `anonimizacao`, `llm`, `rag`, `evolucoes` (esqueleto models/schemas/service/router pronto para preencher). Backend em `127.0.0.1:8010`. Detalhes de deploy na seção **Operação & Deploy**.

**Aderência que o usuário mais cobra:** citar as **§** da `arquitetura.md` em cada mudança; isolamento **no motor** da BD, nunca só na app (§2.1 — padrão já usado: RLS+FORCE, FK composto `(tenant_id, id)`).

---

## 🖥️ Operação & Deploy (contexto do servidor)

> Contexto que **não** se deduz do código — ler antes de mexer no ambiente.

- **Repositório:** `github.com/GA55555/projeto_agenda`, branch **`main`**. Dev local em WSL (`/home/hades/dev/agenda_de_atendimentos`) → commit/push. **Servidor só faz `git pull`** (nunca commitar/pushar do servidor).
- **Servidor:** Debian (`hadesserver`), Docker 29 + Compose v2. Projeto em `~/vscode/config/workspace/projeto_agenda`. Já roda outros serviços (Portainer, n8n, code-server, homarr, pgAdmin de outro projeto).
- **Comandos Docker rodam de dentro de `infra/`** com `--env-file ../.env` (o compose está em `infra/`, o `.env` na raiz). Ex.: `cd infra && docker compose --env-file ../.env up -d`.
- **Portas:** backend publicado em `127.0.0.1:8010` (`BACKEND_HOST_PORT` — a 8000 é do Portainer). Postgres **sem** porta exposta. Sem GUI de admin (só `psql` via `exec`, §2.1.1).
- **`.env` (fora do git, `chmod 600`):** segredos gerados **no servidor** (`POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, `JWT_SECRET_KEY`, `DATABASE_URL` com a senha do `agenda_app`). Ao adicionar variáveis novas ao `.env.example`, lembrar que o `.env` do servidor **não** é atualizado pelo `git pull` — editar à mão.
- **Deploy padrão de código:** `git pull` → `docker compose --env-file ../.env up -d --build [backend]` → `docker compose --env-file ../.env exec backend alembic upgrade head`.
- **⚠️ Roles/init:** mudanças em `infra/postgres/init/*` (ex.: novo role) só reaplicam com **`docker compose --env-file ../.env down -v`** (recria o volume `pgdata`). Migrations aditivas **não** precisam. Dados atuais são **descartáveis** (só há 1 tenant de teste).
- **Bootstrap de usuário:** `docker compose --env-file ../.env exec backend python -m app.cli criar-tenant-usuario --nome ... --email ... --senha ...`.
- **Dados atuais:** 1 psicóloga de teste — `teste@clinica.local` / senha `SenhaForte123` (slug `teste`). Descartável.
- **Provas rápidas:** RLS na BD → `infra/postgres/checks/verify_rls.sql`; liveness `GET /health`; readiness `GET /health/ready`; login `POST /api/v1/auth/login` (form `username`/`password`).
- **Validação local (WSL, sem Docker):** `py_compile` + venv de teste (imports + `pytest tests/unit`). Testes de **integração** e `docker compose up` só rodam **no servidor** (têm BD). `pytest` não está na imagem de produção (é dep `[dev]`).

---

## 🗺️ Visão Geral das Fases

| # | Fase | Objetivo central | Status |
| --- | --- | --- | --- |
| 0 | Fundações & Infra Base | Esqueleto do repositório, Docker e limites de RAM | ✅ Concluído |
| 1 | Base de Dados & Multitenancy | PostgreSQL + pgvector + RLS funcionando | ✅ Concluído |
| 2 | Backend Core (FastAPI) | API base, auth, injeção de tenant | ✅ Concluído |
| 3 | Modelo de Domínio & Consentimento | Pacientes, responsáveis, TCLE, auditoria | ✅ Concluído |
| 3.5 | Agenda de Atendimentos | Agendamentos vinculados a paciente + tenant | ✅ Concluído |
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

> ✅ **Concluído 2026-07-17 no servidor Debian.** postgres + backend `healthy`; extensão `vector` ativa; `/health`→`{"status":"ok"}`. **Nota de infra:** a 8000 do host é ocupada pelo Portainer → backend publicado em `127.0.0.1:8010` via `BACKEND_HOST_PORT=8010` no `.env`. Frontend fica para a Fase 7.

---

## Fase 1 — Base de Dados & Multitenancy (RLS)

**Objetivo:** PostgreSQL afinado, pgvector instalado e isolamento por RLS provado com teste.

**Regras de ouro aplicáveis:** §1.1 (1.5 GB), §1.2 (postgresql.conf), §2.1 (RLS), §3.1 (sem índice vetorial).

### Tarefas
- [x] Imagem Postgres com extensão `pgvector` (`CREATE EXTENSION vector`). *(adiantado na Fase 0: imagem `pgvector/pgvector:pg16` + `infra/postgres/init/01-extensions.sql`)*
- [x] `postgresql.conf` afinado: `shared_buffers` 512MB, `work_mem` 8MB, `maintenance_work_mem` 128MB, `max_connections` 50 (§1.2). *(adiantado na Fase 0: `infra/postgres/postgresql.conf`)*
- [x] Ferramenta de migrations (Alembic): `alembic.ini`, `migrations/env.py` (URL admin via settings, nunca no ini), template.
- [x] Migration inicial `0001`: tabela `tenants` (`id UUID` default `gen_random_uuid()`, `nome`, `slug`, `ativo`, timestamps).
- [x] Padrão `tenant_id` + RLS centralizado no helper `app/db/rls.py` (fonte única), pronto para as tabelas clínicas da Fase 3.
- [x] **Dois roles distintos:** `agenda_admin` (migração/owner, superusuário) × `agenda_app` (`NOSUPERUSER NOBYPASSRLS`, provisionado no init `02-roles.sh`) — RLS atua sobre a aplicação (§2.1.1).
- [x] Ativar RLS + política `tenant_isolation` com `current_setting('app.current_tenant_id')` — **fail-closed** (`nullif` → sem contexto retorna vazio) (§2.1).
- [x] **`FORCE ROW LEVEL SECURITY`** aplicado via helper (nem o dono escapa) (§2.1.1).
- [ ] Índices B-Tree sobre `tenant_id` e `paciente_id` — junto das tabelas clínicas (Fase 3, §3.2).
- [x] **Teste de isolamento:** `tests/integration/test_rls_isolation.py` (pytest) + `infra/postgres/checks/verify_rls.sql` (psql, via `SET ROLE agenda_app`) — provam isolamento T1/T2 e fail-closed.

### Definition of Done
- Teste automatizado de *cross-tenant leakage* passa (retorno vazio para tenant errado). ✅
- **Nenhum** índice vetorial criado (Pesquisa Exata, §3.1). ✅

> ✅ **Concluído e validado no servidor 2026-07-18.** `alembic upgrade head` aplicou `0001`; `verify_rls.sql` → **`RLS OK`** (T1 vê só T1, T2 só T2, sem contexto = vazio/fail-closed). Role `agenda_app` confirmado sem Superuser/Bypass RLS.

---

## Fase 2 — Backend Core (FastAPI)

**Objetivo:** API base com autenticação e injeção automática do contexto de tenant por transação.

**Regras de ouro aplicáveis:** §1.3 (lazy loading, 2 workers, uvloop, GC), §2.1 (`SET LOCAL`), §4.1 (JWT via secrets).

**Decisão:** **tenant = psicóloga** (fronteira de isolamento). `usuarios` = control-plane (email global, sem RLS); tabelas clínicas mantêm RLS+FORCE.

### Tarefas
- [x] Estrutura FastAPI + SQLAlchemy + pool (`pool_size=5, max_overflow=5`) como `agenda_app` (`app/db/session.py`).
- [x] Dockerfile **multi-stage** `slim`; `uvicorn --workers 2 --loop uvloop` (§1.3). *(Fase 0)*
- [x] `gc.set_threshold(700, 10, 10)` no arranque (§1.3). *(Fase 0)*
- [x] Autenticação JWT, login das psicólogas (`core/security.py` bcrypt+JWT, `modules/auth/*`, `POST /auth/login`, `GET /auth/me`).
- [x] **Dependência `get_tenant_session` que executa `SET LOCAL` (via `set_config` local) dentro da transação** de cada request autenticado (`app/db/deps.py`) (§2.1).
- [x] Tabela `usuarios` (migration `0002`) + CLI `criar-tenant-usuario` (bootstrap).
- [x] `GET /tenants/atual` (prova RLS pela API) + convenção de imports lazy documentada (§1.3).
- [x] Healthcheck: `/health` (liveness) + `/health/ready` (SELECT 1).

### Definition of Done
- Request autenticado só enxerga dados do seu tenant (RLS + `SET LOCAL` validados juntos). ✅
- Backend arranca com ≤ 2 workers e respeita `mem_limit` de 1 GB. ✅

> ✅ **Concluído e validado no servidor 2026-07-18.** Login → JWT; `GET /tenants/atual` devolve só o tenant do JWT (RLS via `SET LOCAL`); senha errada → 401; `/health/ready` → 200. Migration `0002` aplicada; 1ª psicóloga criada via CLI.
> **Bug corrigido:** `passlib` 1.7 × `bcrypt` ≥4.1 → migrado para a lib `bcrypt` direta.

---

## Fase 3 — Modelo de Domínio & Consentimento

**Objetivo:** modelar pacientes (menores), responsáveis legais, consentimento e auditoria imutável.

**Regras de ouro aplicáveis:** §2.2 (ECA/LGPD Art. 14, TCLE, auditoria indelével).

**Decisões de domínio (2026-07-18):** vínculo responsável↔paciente **N:N** (tabela `vinculos_resp_paciente` com `tipo_vinculo`/`detem_guarda`/`principal`) — suporta pai+mãe, guarda compartilhada, irmãos; auditoria = **log genérico append-only** (`auditoria`), imutabilidade imposta no BD (**REVOKE UPDATE/DELETE + trigger** `BEFORE UPDATE OR DELETE`); TCLE grava metadados+texto/versão (geração de PDF fica p/ Fase 8/n8n); agendamentos movidos p/ **Fase 3.5**.

### Tarefas
- [x] Tabela `responsaveis_legais` (perfil detalhado). CPF único **por tenant** (PII sob RLS).
- [x] Tabela `pacientes` **sempre** vinculada a responsável legal — invariante imposto na criação (transação única: paciente + ≥1 vínculo + TCLE).
- [x] Tabela `consentimentos` (TCLE): `finalidade_clinica`/`limitacoes_acesso` obrigatórias, termo (versão+texto), data, responsável, quem concedeu.
- [x] Distinção de acesso registrada no TCLE (`limitacoes_acesso`). *Imposição sobre o conteúdo clínico (evoluções) entra na Fase 5+.*
- [x] Tabela de **auditoria imutável** (append-only) — REVOKE + trigger no BD; helper `audit.service.registrar_evento` (revogação de consentimento já grava; guarda entra com a edição de vínculo).
- [x] Endpoints CRUD respeitando RLS (`/responsaveis`, `/pacientes`, `/consentimentos`, `/auditoria` read-only).
- [→] Agendamentos vinculados a paciente + tenant → **movido para a Fase 3.5**.
- [x] Índices B-Tree de pré-filtragem por `tenant_id`/`paciente_id` (§3.2).

### Definition of Done
- Impossível criar paciente sem responsável legal e sem TCLE registrado. ✅ *(schema + serviço transacional; testes unitários provam a rejeição)*
- Revogações/alterações ficam em log inalterável e auditável. ✅ *(auditoria append-only; teste de integração prova UPDATE/DELETE bloqueado)*

> ✅ **Concluída e validada no servidor 2026-07-18.** `alembic upgrade head` aplicou `0003`. Provado por API/psql: criação de paciente+vínculo+TCLE em transação única (RLS `WITH CHECK`, grants, FK composto sob FORCE RLS); resposta traz vínculos+responsável aninhados; CPF normalizado; revogação de TCLE gera evento em `auditoria`; `UPDATE` na auditoria barrado pelo trigger **até para o superusuário** (`ERROR: auditoria e append-only`).

---

## Fase 3.5 — Agenda de Atendimentos

**Objetivo:** agenda de atendimentos vinculada a paciente + tenant (desmembrada da Fase 3 para manter o foco em domínio/consentimento).

**Regras de ouro aplicáveis:** §2.1 (RLS + `tenant_id`), §3.2 (índices B-Tree).

**Decisões (2026-07-19):** anti-sobreposição **no motor** via `EXCLUDE` (btree_gist, `tstzrange(inicio,fim,'[)')`) — atendimentos encostados (fim==início) permitidos; agenda **não** exige TCLE (consentimento é pré-req do prontuário, Fase 5+); status `agendado/realizado/cancelado/falta`, cancelamento **soft** (`motivo_cancelamento`, sem DELETE); paciente por **FK composto** `(tenant_id, paciente_id)` (§2.1); datetimes com timezone obrigatório.

### Tarefas
- [x] Tabela `agendamentos` (`tenant_id`, `paciente_id`, `inicio`, `fim`, `status`, `tipo?`, `observacao`, `motivo_cancelamento`, timestamps) + RLS/FORCE.
- [x] Índices B-Tree `(tenant_id, inicio)` e `paciente_id` (§3.2).
- [x] Endpoints CRUD sob RLS (`POST/GET`, `GET/PATCH /{id}`, `POST /{id}/cancelar`); sobreposição → 409, paciente fora do tenant → 422.
- [x] Estados do atendimento + **não-sobreposição imposta no BD** (`EXCLUDE`, §2.1).

### Definition of Done
- Agendamento sempre vinculado a paciente do tenant (RLS provado). ✅
- Nenhum agendamento cruza tenants. ✅ *(FK composto + RLS; teste de integração)*

> ✅ **Concluída e validada no servidor 2026-07-19.** `alembic upgrade head` → `0004` (extensão `btree_gist` + tabela). Smoke via API: agendamento criado (`agendado`); sobreposição rejeitada (**409** pelo `EXCLUDE`). Review de alto esforço aplicado (4 correções: PATCH 422, timezone, alias `status`, teste RLS).

---

## Fase 4 — Pipeline de Pseudonimização (Túnel Opaco)

**Objetivo:** anonimização/desanonimização local, síncrona e reversível — pré-requisito para qualquer chamada ao LLM.

**Regras de ouro aplicáveis:** §2.3 (Aho-Corasick, dicionário volátil, nunca persistir PII), §1.3 (lazy loading de libs pesadas).

### ❓ Decisões de design a resolver antes de codar (perguntar via AskUserQuestion)
- **Fonte das entidades PII**: de onde vêm os termos a mascarar? (nome do paciente + responsáveis vinculados + clínica/tenant + locais conhecidos) — montados a partir das tabelas da Fase 3, ou também extração por NER do Presidio para PII não-cadastrada (CPF, telefone, endereço no texto livre)?
- **Escopo/ciclo de vida do dicionário volátil**: por requisição (mais seguro, sem estado entre chamadas) vs. por “sessão” de edição de evolução. Onde vive (memória do processo) e como garante-se que morre com a requisição — nunca toca BD/log (§2.3).
- **Granularidade dos marcadores**: `<PERSON_1>`, `<LOCATION_1>`, `<CPF_1>`… — política de numeração sequencial estável dentro do texto.
- **PII não-cadastrada detectada por Regex/NER** (CPF, telefone, e-mail, endereço no texto): mascara também? Como evitar catastrophic backtracking (§2.3 exige Aho-Corasick/regex otimizado).
- **Onde encaixa no fluxo**: módulo `anonimizacao` puro (sem rota agora) consumido pela Fase 6 (LLM), ou já expõe endpoint de teste? Presidio/spaCy entram como dep opcional `[nlp]` no `pyproject` (lazy import, §1.3).
- **Guard-rail de saída**: validação que aborta se algum PII conhecido escapar no payload rumo ao LLM (antecipa Fase 6).

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
- 2026-07-19 — [Fase 3.5] ✅ **Concluída e validada no servidor.** `alembic upgrade head` → `0004` (extensão `btree_gist` + tabela `agendamentos`). Anti-sobreposição **no motor** via `EXCLUDE` (GiST, `tstzrange '[)'`); FK composto `(tenant_id, paciente_id)`; RLS+FORCE; status agendado/realizado/cancelado/falta, cancelamento soft. Smoke API: criar → `agendado`; sobrepor → **409**. Review de alto esforço aplicado (PATCH parcial→422, datetime tz obrigatório, filtro `status` aliased, teste RLS da agenda). Módulo `agendamentos` (models/schemas/service/router) + router na API.
- 2026-07-18 — [Fase 3] ✅ **Concluída e validada no servidor.** `alembic upgrade head` → `0003`. Smoke via API/psql: paciente+vínculo+TCLE em transação única (RLS WITH CHECK + grants + FK composto sob FORCE RLS); resposta com vínculos+responsável; CPF normalizado (`11122233344`); revogação → evento `consentimento_revogado` em `auditoria`; `UPDATE` na auditoria → `ERROR: auditoria e append-only` (trigger barra até superusuário). §2.1/§2.2 provados ponta a ponta.
- 2026-07-18 — [Fase 3] Construída (validar no servidor). **Decisões:** vínculo resp↔paciente **N:N** (`vinculos_resp_paciente`); auditoria = **log genérico append-only** com imutabilidade no BD (REVOKE UPDATE/DELETE + trigger); TCLE grava metadados+texto (PDF fica p/ Fase 8); **agendamentos → Fase 3.5**. Migration `0003` cria `responsaveis_legais`, `pacientes`, `vinculos_resp_paciente`, `consentimentos`, `auditoria` (todas RLS+FORCE, índices §3.2, CHECK de `tipo_vinculo`). Módulos preenchidos (models/schemas/service/router) + 4 routers na API. Invariante do DoD (paciente exige responsável+TCLE) imposto por schema + criação transacional. Validado local: 8 unit tests + render offline do SQL da migration. Testes de integração (RLS + auditoria imutável) aguardam BD no servidor.
- 2026-07-18 — [Fase 2] ✅ **Concluída e validada no servidor.** Login → JWT; `/tenants/atual` só o tenant do JWT (RLS via `SET LOCAL`); senha errada → 401; `/health/ready` → 200. 1ª psicóloga criada via CLI. Bug passlib×bcrypt corrigido.
- 2026-07-18 — [Fase 2] Construída (validar no servidor). **Decisão: tenant = psicóloga.** Sessão/pool como `agenda_app`; auth JWT (bcrypt+PyJWT); `get_tenant_session` injeta `SET LOCAL` por transação; migration `0002` (`usuarios`, control-plane); CLI `criar-tenant-usuario`; `GET /tenants/atual` prova RLS pela API; `/health/ready`. **Bug corrigido:** passlib×bcrypt≥4.1 → lib `bcrypt` direta. Validado local: unit tests + rotas + `/health` 200.
- 2026-07-18 — [Fase 1] ✅ **Concluída e validada no servidor.** `alembic upgrade head` aplicou `0001` (tabela `tenants` + RLS `FORCE`); `verify_rls.sql` → `RLS OK` (isolamento T1/T2 + fail-closed provados); role `agenda_app` sem Superuser/Bypass RLS. Isolamento multitenant garantido no motor da BD (§2.1).
- 2026-07-17 — [Fase 1] Construída (validar no servidor): Alembic (`env.py` usa role admin via settings); migration `0001` cria `tenants` + RLS `tenant_isolation` **FORCE**, fail-closed; helper único `app/db/rls.py`; role `agenda_app` (`NOSUPERUSER NOBYPASSRLS`) via init `02-roles.sh`; `config.py` com URLs admin/app; teste `test_rls_isolation.py` + `verify_rls.sql` (SET ROLE). Validado local: imports + render do SQL de RLS OK. **Deploy exige `docker compose down -v`** (dados descartáveis) p/ o init criar o role.
- 2026-07-17 — [Fase 0] ✅ **Fase 0 concluída e validada no servidor Debian.** `docker compose up` sobe postgres (`healthy`, ~52 MB) + backend (`healthy`), extensão `vector` 0.8.5, `/health`→200. Ajuste: `BACKEND_HOST_PORT=8010` (Portainer ocupa a 8000). Repo do servidor reconciliado (`master`→`main`, remote `origin` adicionado).
- 2026-07-17 — [Fase 0/1] Rota 1: `infra/postgres/postgresql.conf` afinado (§1.2, sem log de statements p/ evitar PII) + `init/01-extensions.sql` (pgvector, sem índice §3.1); backend `pyproject.toml` + `Dockerfile` multi-stage slim (§4.1) + app mínimo runnable (`/health`, GC §1.3); `infra/docker-compose.yml` (postgres 1.5GB + backend 1GB, `mem_limit` §1.1; BD sem porta exposta; backend só no localhost). Validado local: app boota e `/health`→200. Docker não roda neste WSL; `docker compose up` fica p/ o servidor Debian (requer criar `.env`).
- 2026-07-17 — [Docs] Avaliada administração da BD. **Decisão: sem GUI** — acesso por `psql` via `docker compose exec` (menor exposição, §0.3; 0 MB, §1.1). pgAdmin descartado. Mantida a **§2.1.1 (nova regra)**: role de app sem privilégio + `FORCE ROW LEVEL SECURITY`; o superusuário/`psql` ignora o RLS por desenho e é *break-glass*. Docs (§0.2, §1.1, §2.1.1, §4.1, §5) e Fases 0/1/9 reconciliados. Debian já constava.

---

## ⚖️ Decisões em Aberto (a resolver)

- [ ] **Framework do frontend:** React ou Vue.js? (Fase 7)
- [x] **Localização dos docs:** `docs/`. ✔ Resolvido 2026-07-17.
- [x] **Layout do backend:** por domínio/módulo. ✔ Resolvido 2026-07-17.
- [x] **Vínculo responsável↔paciente:** N:N (`vinculos_resp_paciente`). ✔ Resolvido 2026-07-18 (Fase 3).
- [x] **Auditoria:** log genérico append-only, imutabilidade no BD (REVOKE + trigger). ✔ Resolvido 2026-07-18. *Hash-chain fica como reforço futuro opcional (§2.2).*
- [ ] Provedor/modelo de embeddings confirmado como `text-embedding-3-small`? (Fase 5)
- [ ] Estratégia de rotação de segredos (Docker Secrets vs. `.env`). (Fase 0)

*Registre aqui toda decisão arquitetural que fugir do `arquitetura.md` e a justificativa.*
