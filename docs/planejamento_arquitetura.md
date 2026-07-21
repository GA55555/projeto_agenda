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
| Fase corrente | **Fase 7h (UX do dashboard) construída, validada, commitada e enviada (`0ef55b1`).** Servidor deployado até **7e (migration `0007`)**; **7f + 7g + 7h pendentes de deploy**. Depois: **Fase 8 (n8n & Backups)** |
| Última atualização | 2026-07-21 |
| Bloqueios ativos | Nenhum |
| Próximo passo imediato | **1) Rotacionar a credencial de teste antes versionada. 2) Deployar 7f+7g+7h no servidor**: `git pull` → `cd infra` → `docker compose --env-file ../.env up -d --build backend frontend` → **`alembic upgrade head` (migration `0008`, obrigatória p/ a 7f)**; validar calendário→novo agendamento, consulta mensal, recorrência e cartões. **3) Depois, planejar a Fase 8 (§4.2).** |

> Atualize esta tabela ao fim de cada sessão de trabalho.

### 🔖 Ponto de Retomada (ler primeiro na próxima sessão)

**Onde paramos (2026-07-21):** Fases **0–7h construídas, revisadas e commitadas**. `main`, `origin/main` e `HEAD` estavam sincronizados no commit **`0ef55b1`** na última verificação local; **última migration = `0008`**.

- **Estado de deploy do servidor:** deployado e validado até a **7e (`alembic current` = `0007`)**. **7f (`65d8a7b`, migration `0008`), 7g (`5603392`) e 7h (`0ef55b1`) NÃO foram deployadas ainda** — ver "Próximo passo imediato".
- **Sub-fases da Fase 7 (todas commitadas):** 7a/7b/7c (deployadas) · **7d** (`d6f3a95`): ações na agenda (realizado/falta/cancelar), `GET /dashboard/resumo`, **perfil** (`PATCH /auth/me`+senha; **migration `0006` GRANT UPDATE em `usuarios`** — sem ela o "alterar nome" dá 500, foi a causa do bug relatado) · **7e** (`e5b2d7c`): agenda por cliques + apagar; **arquivar/apagar paciente** (apagar bloqueado com prontuário, CFP §0.3); **evolução ↔ atendimento REALIZADO** (**migration `0007`**); dashboard histórico (dia/mês, cancelados, tooltips); responsável 18+ · **7f** (`65d8a7b`): **calendário** no dashboard (`GET /dashboard/{dia,mes,calendario}`, dashboard dividido dia/mês) + **recorrência** de agendamento (série materializada `serie_id`/`serie_frequencia`, **migration `0008`**; desfazer via `/agenda/:id`) · **7g** (`5603392`): polimento de UX (fonte maior, espaçamento, badge do calendário, **cartões de paciente** com observações editáveis inline). Detalhe de cada uma na seção da Fase 7 abaixo.
- **⚠️ Regra de fluxo nova (7e):** para gravar uma evolução, o atendimento precisa estar **`Realizado`** na agenda (o editor só lista realizados). Reflete o modelo "evolução documenta sessão que ocorreu".

**Próximo passo imediato (1): ROTAÇÃO + DEPLOY da 7f+7g+7h** — primeiro rotacionar a credencial de teste que apareceu no histórico; depois, o usuário roda no servidor: `git pull` · `cd infra` · `docker compose --env-file ../.env up -d --build backend frontend` · `docker compose --env-file ../.env exec backend alembic upgrade head` (**→ `0008`, obrigatória**). Validar: clique em dia do calendário abre novo agendamento com a data; bloco Hoje antes do calendário; consulta de mês/ano só aplica na lupa; cadastros ativos depois das pendências; recorrência; cartões de paciente.

**Próximo passo imediato (2): planejar a Fase 8 (Automação n8n & Backups, §4.2)** — plano + perguntas de design ANTES de codar. Característica diferente: boa parte vive **dentro do n8n** (já rodando), não no código Python. Escopo: webhook FastAPI→n8n **autenticado** **após a aprovação** de uma evolução; OAuth2 do Google **100% no n8n** (Drive+Docs API; app/BD nunca tocam senhas Google); JSON limpo → PDF/Sheets no diretório da psicóloga; rotina diária `pg_dump` + **WAL** no **HDD 500 GB**; teste de restauração. *Aberto: a "extensão automática" das séries de recorrência (a regra sobrevive em `serie_frequencia`) pode entrar aqui via n8n/cron. E a assinatura eletrônica FORMAL da evolução (hoje "aprovar e gravar" = aprovação auditável) — adiada p/ §8/§9; reavaliar.*

**Fluxo de trabalho (imutável):** plano+perguntas → construir/validar local (WSL, sem Docker: `py_compile` + venv de teste `pytest tests/unit` + render offline do SQL; **frontend**: `npx tsc --noEmit` + `npm run build` — node 22 disponível no WSL) → **revisar com o usuário** (trazer diff/resumo) → `/code-review` alto esforço (usuário quase sempre pede) → **commit direto em `main`** (Co-Authored-By) → **push só quando o usuário pede** → **usuário** faz deploy no servidor e valida → marcar ✅. Comandos ao usuário **uma linha por vez** (terminal quebra pastes compostos). Ver [[feedback-fluxo-trabalho-agenda]].

**⚠️ Lição de deploy (7c):** os **testes de integração só rodam no servidor** (precisam de BD) e **não** são executados no deploy → um bug pego por eles pode escapar. Ex.: `/auth/me` deu 500 em produção porque `PerfilOut.email` era `EmailStr` e o `email-validator` rejeita o TLD `.local` do usuário de teste. **Regra adotada:** *response models (`Out`) usam `str` para e-mail; `EmailStr` só em `Create`/`Update` (entrada)*. Considerar um **smoke pós-deploy** no §9.

**Contexto de ambiente/dados (servidor):** SPA publicada apenas no localhost do servidor e acessada por **túnel SSH/Tailscale iniciado na máquina do usuário**. Endereços, nomes de host, usuários, senhas e identificadores de registros de teste **não são documentados no repositório**; ficam no inventário operacional restrito. O `.env` do servidor mantém as portas locais, o modo de cookie adequado ao transporte atual e a chave OpenAI fora do Git. **Ação obrigatória:** toda credencial que já tenha aparecido no histórico versionado deve ser rotacionada antes do próximo uso. Para testar a criação de evolução (7e+), usar um paciente descartável com TCLE ativo e agendamento **`realizado`**. **Setup de teste local (WSL):** venv py3.12 em scratchpad com `pip install -e '.[dev]'` p/ `pytest tests/unit`; FastAPI 0.139 usa inclusão **lazy** de routers (`app.routes` não expande — checar rotas via `app.openapi()['paths']`). Detalhes não sensíveis ficam na seção **Operação & Deploy**.

**Aderência que o usuário mais cobra:** citar as **§** da `arquitetura.md` em cada mudança; isolamento **no motor** da BD, nunca só na app (§2.1 — RLS+FORCE, FK composto `(tenant_id, id)`); túnel opaco de PII (§2.3) e superfície IA↔BD (§3.4) nas partes de IA.

---

## 🖥️ Operação & Deploy (contexto do servidor)

> Contexto que **não** se deduz do código — ler antes de mexer no ambiente.

- **Repositório:** `github.com/GA55555/projeto_agenda`, branch **`main`**. Dev local em WSL (`/home/hades/dev/agenda_de_atendimentos`) → commit/push. **Servidor só faz `git pull`** (nunca commitar/pushar do servidor).
- **Servidor:** Debian 12, Docker 29 + Compose v2. Nome do host, endereço e caminho operacional ficam no inventário restrito. Já roda outros serviços (Portainer, n8n, code-server, Homarr e serviços de outros projetos).
- **Comandos Docker rodam de dentro de `infra/`** com `--env-file ../.env` (o compose está em `infra/`, o `.env` na raiz). Ex.: `cd infra && docker compose --env-file ../.env up -d`.
- **Portas:** backend publicado em `127.0.0.1:8010` (`BACKEND_HOST_PORT` — a 8000 é do Portainer). **Frontend (SPA) em `127.0.0.1:8090`** (`FRONTEND_HOST_PORT` — a 8080 é do Homarr → `/board`). Postgres **sem** porta exposta. Sem GUI de admin (só `psql` via `exec`, §2.1.1). O browser fala **só com o Nginx** (`8090`), que faz proxy de `/api`→backend.
- **`.env` da Fase 7:** `FRONTEND_HOST_PORT=8090` e **`COOKIE_SECURE=false`** (deploy HTTP; sob TLS no §9 vira `true`, senão o cookie `Secure` não gruda e o login falha silenciosamente).
- **`.env` (fora do git, `chmod 600`):** segredos gerados **no servidor** (`POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, `JWT_SECRET_KEY`, `DATABASE_URL` com a senha do `agenda_app`). Ao adicionar variáveis novas ao `.env.example`, lembrar que o `.env` do servidor **não** é atualizado pelo `git pull` — editar à mão.
- **Deploy padrão de código:** `git pull` → `docker compose --env-file ../.env up -d --build [backend]` → `docker compose --env-file ../.env exec backend alembic upgrade head`.
- **Fase 7 (SPA):** deploy `up -d --build backend frontend` (sem migration na 7b/7c). **⚠️ 7d (fechamento) TEM migration:** `alembic upgrade head` → **`0006`** (GRANT UPDATE em `usuarios` p/ o perfil; sem ela, PATCH /auth/me e troca de senha dão 500 por privilégio). Acesso via túnel Tailscale (acima). Validar: login por cookie (`COOKIE_SECURE=false` em HTTP), dashboard, wizard de paciente, agendar (409 se sobrepor), CPF duplicado → 409. **Gotcha:** *response models (`Out`) usam `str` para e-mail, não `EmailStr`* — o `email-validator` rejeita TLDs reservados (`.local`) na serialização e derruba o endpoint (aconteceu no `/auth/me`).
- **Fase 5 (RAG):** deploy padrão + **`alembic upgrade head`** (migration `0005`: `evolucoes` + `evolucao_chunks`). Adicionar **`OPENAI_API_KEY`** ao `.env` do servidor à mão (o `git pull` não toca o `.env`). Sem a chave, evoluções são criadas normalmente e os embeddings ficam **pendentes** (null) até a chave existir. `pgvector`/`openai` já entram no build (deps base).
- **Fase 4 (NER):** o `Dockerfile` do backend **já instala** o extra `[nlp]` + baixa `pt_core_news_sm` (modelo pequeno, §1.1) no build — NER ativo após `up -d --build backend`, sem passo manual. Import lazy (§1.3). Flag `NER_HABILITADO` no `.env` liga/desliga; sem o extra o pipeline degrada gracioso (só Aho-Corasick + regex). **Não** há migration na Fase 4.
- **⚠️ Roles/init:** mudanças em `infra/postgres/init/*` (ex.: novo role) só reaplicam com **`docker compose --env-file ../.env down -v`** (recria o volume `pgdata`). Migrations aditivas **não** precisam. Dados atuais são **descartáveis** (só há 1 tenant de teste).
- **Bootstrap de usuário:** `docker compose --env-file ../.env exec backend python -m app.cli criar-tenant-usuario --nome ... --email ... --senha ...`.
- **Dados atuais:** ambiente de teste descartável. Credenciais e identificadores vivem somente no inventário operacional restrito, nunca neste documento.
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
| 4 | Pipeline de Pseudonimização | Túnel opaco anonimizar/desanonimizar (Aho-Corasick) | ✅ Concluído |
| 5 | IA Vetorial & RAG | Embeddings, filtragem híbrida, chunking | ✅ Concluído |
| 6 | Integração LLM (OpenAI) | Geração de evoluções via túnel de pseudonimização | ✅ Concluído |
| 7 | Frontend (SPA) | Interface das psicólogas, aprovação de evoluções | ✅ Concluído |
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

**Decisões de design (2026-07-19, via AskUserQuestion):** fonte = **cadastrado (Aho-Corasick) + NER (Presidio) lazy** para PII de texto livre; ciclo do dicionário volátil = **por requisição** (nasce/morre no request, sem estado entre chamadas); entrega = **módulo puro** (sem rota/tabela/migration) consumido pela Fase 6; modelo NER = **`pt_core_news_sm` (pequeno)** para caber no `mem_limit` de 1 GB (§1.1) — camada NER atrás do extra `[nlp]` + flag `ner_habilitado`. Marcadores `<CAT_n>` sequenciais por 1ª aparição, idempotentes por trecho exato (round-trip exato). Sobreposição: **mais longo vence** + fronteira de palavra.

### Tarefas
- [x] Motor de deteção com **Aho-Corasick** (puro, stdlib) + Regex ancorado; Presidio como reforço, importado lazy (§1.3/§2.3). *(`automaton.py`, `recognizers.py`, `nlp.py`)*
- [x] Fonte de entidades PII do paciente (nome, familiares, clínica) sob RLS para alimentar o autômato. *(`sources.py`)*
- [x] `Anonymizer`: mapeia PII → marcadores sequenciais (`<PERSON_1>`, `<LOCATION_1>`). *(`pseudonimizador.py`)*
- [x] **Dicionário de equivalência em memória volátil** (`MapaPseudonimizacao`) — não é model, sem serializador, `__repr__` esconde valores; **jamais gravado na BD** (§2.3).
- [x] `Deanonymizer`: restaura marcadores no texto de resposta. *(`pseudonimizador.desanonimizar`)*
- [x] **Guard-rail de saída** (`guardrail.verificar_sem_pii`) — aborta (`PIIVazadaError`) se PII conhecida escapar (antecipa Fase 6).
- [x] Testes unitários: round-trip preserva o texto; nenhum PII escapa; dicionário não persiste; fronteira de palavra; regex; anti-backtracking. **35 passed, 1 skipped** (NER só roda com o extra `[nlp]`).

### Definition of Done
- Teste prova que texto enviado "para fora" não contém PII. ✅ *(guard-rail + round-trip; validar no servidor com o NER ligado)*
- Teste prova que o dicionário não é persistido em lugar nenhum. ✅ *(não é `Base`; sem `models.py`/`router.py`/migration; `__repr__` não vaza)*

> ✅ **Concluída e validada no servidor (2026-07-19).** Build instalou `[nlp]` + `pt_core_news_sm`. Smoke por dentro do container: Pedro→`<PERSON_1>`, CPF→`<CPF_1>`, **round-trip exato**, **guard-rail** detecta PII que escaparia. **NER provado**: `João Silva`→PERSON, `São Paulo`/`Belo Horizonte`→LOCATION (mapeamento PER→PERSON OK, achado #3 resolvido). Code-review de alto esforço → **5 achados aplicados**: (#1) offset via `_fold` que preserva comprimento no caseless; (#2) O(n²) no `desanonimizar`; (#3) mapeamento explícito de rótulos NER; (#4) removido `presidio-anonymizer` não usado; (#5) desempate de categoria determinístico. **Limitação conhecida:** o modelo `sm` tem recall menor (ex.: não pegou "Lucas" em contexto pobre) — aceitável, o NER é *reforço*; PII de paciente/família é **cadastrada** (Aho-Corasick). RAM idle do backend: 165 MB (o modelo NER carrega lazy por processo, só na Fase 6 aparece nos workers — vigiar o orçamento de 1 GB, §1.1).

---

## Fase 5 — IA Vetorial & RAG (pgvector)

**Objetivo:** memória longitudinal do paciente via embeddings, com filtragem híbrida e chunking.

**Regras de ouro aplicáveis:** §3.1 (sem índice), §3.2 (filtragem híbrida obrigatória), §3.3 (chunking), **§3.4 (superfície IA↔BD: só vetorizar texto anonimizado; RAG sob RLS; guard-rail nos embeddings)**.

**Decisões de design (2026-07-19, via AskUserQuestion):** (1) **nota crua** no BD sob RLS + **embedding só do texto anonimizado** (re-anonimiza no uso, Fase 6); (2) embeddings **síncronos**, nota **persiste mesmo se a OpenAI falhar** (chunk fica `embedding` pendente/null, re-embed depois); (3) criar evolução **exige TCLE ativo** (§2.2, gate no serviço); (4) escopo = tabelas+chunking+embed+retrieval+endpoints, **sem LLM** (Fase 6). Marcadores canonicalizados (`<PERSON_1>`→`<PERSON>`) só para o vetor (reduz ruído).

### Tarefas
- [x] Tabela `evolucoes` (nota crua) + `evolucao_chunks` com coluna `embedding vector(1536)`; RLS+FORCE, FK composto, migration `0005`.
- [x] Estratégia de **chunking** (`chunking.py`): parágrafos + subdivisão por frase com overlap.
- [x] Serviço de embeddings (`embeddings.py`, OpenAI **lazy** §1.3, timeout curto) — texto **já anonimizado** (§3.4) + guard-rail antes da chamada.
- [x] Consulta RAG (`service.buscar_contexto`) pré-filtrada por `tenant_id`+`paciente_id`, depois `ORDER BY embedding <=> $vetor LIMIT k` (§3.2).
- [x] **Ausência de índice vetorial** confirmada no render da migration (Pesquisa Exata, §3.1).
- [x] Gate de **consentimento ativo** (§2.2) + endpoints CRUD (`POST/GET /evolucoes`).
- [~] Testes de recall/latência com dados sintéticos → **movido p/ Fase 6** (quando houver geração real e chave OpenAI no servidor).

### Definition of Done
- Query RAG nunca roda sem os filtros de tenant/paciente. ✅ *(filtro explícito no `buscar_contexto` + RLS; teste do filtro fica p/ Fase 6)*
- Latência da busca exata < 50 ms no volume esperado. *(validar no servidor com dados)*

> ✅ **Concluída e validada no servidor (2026-07-19).** `alembic upgrade head` → `0005`. Provado por psql/API: RLS FORCE nas 2 tabelas (`relforcerowsecurity=t`), coluna `embedding vector(1536)`, índices só B-Tree (**sem `ivfflat`/`hnsw`**, §3.1). Smoke via API: criar evolução p/ paciente com TCLE revogado → **422** (gate §2.2); paciente com consentimento → **201** com `total_chunks:2` (chunking §3.3) e `embeddings_pendentes:2` (sem chave OpenAI ativa → **nota persiste**, degradação graciosa da decisão Fase 5). Code-review de alto esforço → **#1/#2/#4 aplicados** (timeout OpenAI; contagem via `COUNT` sem materializar o vetor; grant sem DELETE §2.1.1). **Registrados p/ depois:** #3 (reuso de entidades/autômato por evolução), #5 (guarda de dimensão do vetor vs. modelo), #6 (teste do filtro híbrido do retrieval — Fase 6).

---

## Fase 6 — Integração LLM (OpenAI)

**Objetivo:** gerar resumos/evoluções clínicas passando **exclusivamente** por texto anonimizado.

**Regras de ouro aplicáveis:** §2.3 (só texto mascarado sai), §3.3 (prompt dinâmico com contexto recuperado), **§3.4 (LLM sem tool de BD; separação instrução/dado; guard-rail em toda saída; OpenAI retenção-zero)**.

**Decisões de design (2026-07-19, via AskUserQuestion):** deliverable = **rascunho de evolução + destaques longitudinais** (resposta em JSON); persistência **stateless** (só retorna; salvar aprovado usa `POST /evolucoes` da Fase 5 na Fase 7 — **sem migration**); modelo **`gpt-4o-mini`** (via env, `temperature` baixa); **gate de TCLE ativo** na geração (§2.2).

### Tarefas
- [x] Montagem de prompt dinâmico (`prompts.py`): nota do dia + blocos históricos (Fase 5), **anonimizados numa única passagem** (marcadores consistentes); instrução separada do dado (§3.4 #5).
- [x] Chamada à OpenAI (`client.py`) recebendo só tokens artificiais; **sem tools** (§3.4 #1), `store=False` (armazenamento desativado na chamada), timeout de chat próprio. A retenção da organização é uma verificação operacional da Fase 9 (§3.4 #6).
- [x] Desanonimização da resposta antes de exibir (Fase 4); marcadores residuais/alucinados limpos.
- [x] **Guard-rail** (§3.4 #4): aborta a chamada (hard-fail, 422) se PII conhecida aparecer no payload de saída.
- [x] Tratamento de erros (OpenAI indisponível → 503; JSON inválido → fallback tolerante).
- [x] Chave OpenAI via `.env` restrito (§4.1); `POST /llm/evolucoes/rascunho`.

### Definition of Done
- Log/inspeção confirma que o payload enviado à OpenAI não tem PII. ✅ *(guard-rail + teste prova que nada de PII crua sai; abortar antes da chamada)*
- Resposta final ao usuário aparece desanonimizada e legível. ✅ *(desanonimização com o mapa volátil; teste de round-trip)*

> ✅ **Concluída e validada no servidor (2026-07-19).** Módulo `llm` stateless (sem tabela/migration). Fluxo: gate TCLE → RAG (`buscar_contexto`) → monta+anonimiza numa passagem → **guard-rail hard-abort** → OpenAI (`gpt-4o-mini`, sem tools, `store=false`) → desanonimiza → rascunho. **55 unit tests** local. Smoke no servidor com `OPENAI_API_KEY` ativa: `POST /llm/evolucoes/rascunho` → **200** com `evolucao` (texto clínico coerente em pt) + `destaques` (lista) + `chunks_contexto` — provou, contra a API viva, o modo `json_object` (achado #2), sem 503 espúrio (achado #1) e o parse JSON→campos. Sem chave → **503** (fail-closed); campo errado → **422** (schema). Code-review de alto esforço → **5 achados aplicados**: (#1) timeout de chat separado (60s); (#2) "json" minúscula no prompt; (#3) limpeza de marcadores residuais; (#4) `anonimizar_com_entidades` reusa entidades (otimiza a Fase 5 tb); (#5) `SemConsentimentoAtivo` centralizada em `consentimentos`.

---

## Fase 7 — Frontend (SPA)

**Objetivo:** interface das psicólogas para agenda, prontuários e **aprovação** de evoluções geradas.

**Regras de ouro aplicáveis:** §1.1 (Nginx 100 MB), §2.2 (separação de acessos), §4.1 (multi-stage), §2.1.1 (backend não-exposto: Nginx faz proxy de `/api`).

**Decisões (2026-07-19, via AskUserQuestion):** **React + Vite + TS**; escopo em **vertical slice** do loop de IA (login→agenda→ficha→gerar→aprovar→gravar); **token JWT em cookie httpOnly** (SameSite strict; `Secure` sob TLS no §9); **só psicólogas** agora (portal dos pais §2.2 fica p/ fase própria). Dividida em **7a (fundação)** e **7b (telas)**.

### Tarefas — 7a (fundação) ✅ construída
- [x] SPA **React + Vite + TS**; Nginx `mem_limit` 100 MB (§1.1), **multi-stage** (§4.1).
- [x] **Nginx serve estáticos + reverse-proxy `/api`→`backend:8000`** (mesma origem, zero CORS, backend não-exposto §2.1.1); CSP + headers de segurança.
- [x] **Auth por cookie httpOnly** no backend (login seta cookie; `get_current_user` lê cookie|bearer; `POST /auth/logout`); dual-mode intencional (bearer p/ curl/testes).
- [x] SPA: cliente de API (`credentials: include`, JS não lê o token), AuthContext (`/auth/me`), handler global de 401, telas Login + Home (prova a sessão).

### Tarefas — 7b (telas) ✅ deployada e validada
- [x] **Agenda do dia** (`GET /agendamentos` filtrado por [de,ate) do dia + mapa de nomes); **ficha do paciente** (dados+responsáveis+**status TCLE**+evoluções). Shell de navegação (Agenda·Pacientes·Sair).
- [x] **Editor de evolução**: nota do dia → `POST /llm/evolucoes/rascunho` → revisar/editar (desanonimizado) → aprovar → `POST /evolucoes`. Trata 422 (mostra `detail` real), 503 (IA), 401 (login).
- [→] Assinatura eletrônica formal → **§9** (decisão: "aprovar e gravar" = aprovação auditável via `autor_usuario_id`+timestamp; assinatura criptográfica depois).
- [~] Distinção de acesso pais × conteúdo (§2.2) → app **só psicólogas** nesta fase; portal dos pais é fase própria.

### Definition of Done
- Fluxo completo: nota → IA → revisão → aprovação → gravação funciona ponta a ponta. ✅ *(validado no browser no servidor, 2026-07-20)*
- Contentor frontend respeita 100 MB. ✅ *(Nginx alpine estático)*

> ✅ **7b deployada e validada no servidor (2026-07-20).** Loop completo percorrido no browser (via túnel SSH/Tailscale): login → agenda → ficha (TCLE ativo) → Nova evolução → **Gerar rascunho (IA)** → revisar → **Aprovar e gravar**. **RAG provado**: após 1-2 evoluções, o rascunho seguinte trouxe `chunks_contexto > 0` (a IA recuperou histórico do próprio paciente) — valida a convergência Fases 4+5+6+7 e os embeddings da Fase 5 finalmente populados/recuperados. Detalhe da construção/review abaixo. ↓
>
> **Histórico:** a 7b foi primeiro validada localmente em 2026-07-19 e depois deployada e validada no servidor em 2026-07-20, conforme o marco acima.
>
> ✅ **7a deployada e validada no servidor (2026-07-19).** Backend: **61 unit tests** (6 novos de cookie/bearer); frontend `build`+`tsc` OK. Code-review → **7 achados, 6 aplicados** (#4 mantido dual-mode de propósito). No servidor: SPA servida (`200`, headers de segurança/CSP), e **auth por cookie httpOnly provado ponta a ponta** — `login`→`/auth/me` só com cookie devolveu o contexto do JWT via Nginx→backend. **Infra do deploy:** porta host **8090** (a 8080 é do Homarr — conflito, igual à 8000/Portainer→8010); **`COOKIE_SECURE=false`** no `.env` (HTTP). Bug do healthcheck (`wget -qO-` não parseia no BusyBox) corrigido p/ `wget -q -O /dev/null`.

### 7c — Melhorias de Frontend (pedido do usuário, 2026-07-20)

**Objetivo:** app mais completo e usável — dashboard, cadastros (agendar, criar paciente/responsável), menu de perfil e um design **sóbrio, efetivo e fácil** (não mais minimalista).

**Decisões (via AskUserQuestion):** começar por **7c.1 (design+navegação)**; criar paciente por **assistente guiado** (responsável novo/existente → dados → TCLE, uma transação); **enriquecer `/auth/me`** com nome/e-mail p/ o menu de perfil; direção visual **clínico calmo** (sidebar clara, cards, acento verde-azulado, espaçamento generoso, badges suaves).

**Incrementos:**
- **7c.1 — Design & Navegação:** design system (paleta clínica, componentes reutilizáveis), **layout com sidebar** (Dashboard·Agenda·Pacientes·Responsáveis) + **menu de perfil** (nome/e-mail/papel + Sair). Backend: `/auth/me` passa a devolver nome/e-mail (1 query, sem migration). Telas Dashboard/Responsáveis entram como placeholder. → ✅ **deployada e validada no servidor (2026-07-20)**; `tsc`+`build` OK, 61 unit tests; code-review aplicado.
- **7c.2 — Cadastros:** criar **agendamento** (form + 409 de sobreposição); **Responsáveis** (lista + criar/editar + detalhe com contato); criar **paciente** (wizard responsável→dados→TCLE). → ✅ **deployada e validada no servidor (2026-07-20)**; `tsc`+`build` OK, backend 61 unit tests; tratamento de CPF duplicado e guards revisados.
- **7c.3 — Dashboard:** visão geral — hoje na agenda, contadores, acesso rápido. → ✅ **deployada e validada no servidor (2026-07-20)**; `tsc`+`build` OK. O agregado de pendências foi entregue depois em `GET /dashboard/resumo` na 7d.

### 7d — Fechamento da Fase 7 (pedido do usuário, 2026-07-20)

**Objetivo:** 3 frentes que faltavam — **ações na agenda** (realizado/falta/cancelar por linha), **`GET /dashboard/resumo`** (indicadores agregados no BD, §2.1/§3.2) e **configuração de perfil** (`PATCH /auth/me` + `POST /auth/me/senha`).

**Decisões (via AskUserQuestion):** perfil edita **nome+e-mail+senha** (troca de senha exige a atual); agenda = realizado/falta/cancelar c/ **motivo opcional** (sem reagendar); dashboard = 3 blocos (hoje / mês c/ taxa de comparecimento e dias com atendimento / pendências: sem TCLE §2.2, sem próximo atendimento, próxima semana).

**Construção:** módulo `dashboard` (**sem model/migration**, agregações únicas sob RLS §2.1, fuso `APP_TIMEZONE`); perfil no módulo `auth`; ações na agenda são frontend-only (PATCH/cancelar já existiam, Fase 3.5). Tela `/perfil` + link na sidebar; `AuthContext.refresh()`.

### 7e — Mudanças e melhorias de UX/gestão (pedido do usuário, 2026-07-20)

**Escopo (6 blocos):** (0) bugfix 500 no PATCH /auth/me *(causa confirmada e resolvida: migration `0006` não aplicada)*; (1) dados & validações; (2) agenda UX; (3) arquivar/apagar paciente; (4) dashboard histórico; (5) responsividade.

**Decisões (via AskUserQuestion):** apagar paciente **bloqueado se houver evoluções** (guarda 5 anos CFP 001/2009 §0.3 — e o role da app **nem tem GRANT DELETE em `evolucoes`**: garantia no motor §2.1.1); **evolução vinculada a agendamento** (data do atendimento vem dele; coluna nullable p/ legadas); apagar agendamento **só status `agendado`** + auditoria; agenda UX = **dia + grade de horários** com duração por clique.

**Construção (migration `0007`):** `evolucoes.agendamento_id` (FK composto `(tenant_id, agendamento_id)` RESTRICT + `UNIQUE(tenant_id,id)` em agendamentos) + GRANTs DELETE (agendamentos, pacientes, vinculos, consentimentos). Backend: `DELETE /agendamentos/{id}` e `DELETE /pacientes/{id}` (409 com prontuário), arquivar/reativar auditados (`TIPO_PACIENTE_*`), responsável **≥18 anos** (validator), `EvolucaoCreate.agendamento_id` obrigatório (+ validação paciente/status; OUTER JOIN traz `data_atendimento` sem N+1), dashboard com **`?dia=&mes=`** (histórico desde `desde` = mês de criação da conta via `tenants.criado_em`; janelas `janela_do_dia`/`janela_do_mes`; cancelados no dia e no mês). Frontend: AgendamentoForm por cliques (grade 07–20h, slots ocupados marcados, chips de duração, **aviso de conflito ao vivo**); Agenda com Apagar; Ficha completa (dados cadastrais + responsáveis com contato + zona de administração arquivar/apagar); Editor exige atendimento; Dashboard com seletores dia/mês + **tooltips ⓘ** explicando cada indicador (`components/Stat.tsx`); Pacientes com filtro de arquivados; ResponsavelForm com `max` de 18 anos; responsivo (cards com overflow-x, `main` 72rem, alvos de toque, grade adaptável). **99 unit tests** (+11), `tsc`+build OK, SQL da 0007 renderizado offline.

**Code-review alto esforço (8 finders + verificação) → 10 achados + itens cortados APLICADOS:** (1+2) **evolução só vincula atendimento `realizado`**; (3) wizard coleta nascimento do responsável com trava 18+; (4) duração customizável; (5) coerência tile×lista do dashboard; (6) editor zera seleção/rascunho ao trocar de paciente; (7) maioridade alinhada no 29/02; (8) consultas consolidadas; (9) índice `(tenant_id, criado_em)`; (10) helpers compartilhados. **99 unit tests**, `tsc`+build OK, SQL 0007 renderizado. → ✅ **commitada, deployada e validada no servidor (`0007`).**

**Code-review alto esforço (8 finders + verificação) → 10 achados APLICADOS:** migration `0006` com privilégio mínimo; limite bcrypt de 72 bytes; e-mail normalizado; máquina de estados; coerência tile×lista; ações sem refetch; reautenticação e auditoria na troca de e-mail; fonte única de TCLE vigente. **88 unit tests**, `tsc`+build OK. → ✅ **commitada, deployada e validada no servidor (`0006`).**

### 7f — Calendário & Recorrência (pedido do usuário, 2026-07-20)

**Objetivo:** (1) **calendário** no dashboard — grade mensal com dias coloridos quando têm consulta; clicar num dia mostra a agenda daquele dia; navega para meses futuros. (2) **Recorrência** no agendamento — repetir mesmo dia/horário sem remarcar; desfazer abrindo um atendimento da série.

**Decisões (via AskUserQuestion):** frequência **semanal + quinzenal + mensal**; horizonte **~6 meses** (`_HORIZONTE_DIAS=183`); desfazer remove **só futuras ainda 'agendado'** (passadas/realizadas ficam); conflito de horário na série → **pula a semana** (best-effort, informa criados/pulados).

**Modelo:** recorrência = **série materializada** (`agendamentos.serie_id`, migration `0008`) — ocorrências futuras são linhas concretas (mantém EXCLUDE, gate de evolução realizado, contadores). Geração com **SAVEPOINT por ocorrência** (`begin_nested`): conflito (EXCLUDE 23P01) pula a cadência sem abortar. Desfazer = `POST /agendamentos/{id}/desfazer-recorrencia` (deleta futuras 'agendado' da série; auditável `recorrencia_desfeita` §2.2). `POST /agendamentos` retorna `AgendamentoCriadoOut` (`serie_criados`/`serie_pulados`). Calendário = `GET /dashboard/calendario?mes=` → `{dia: contagem}` (fuso da clínica, aceita mês futuro). Frontend: `Calendario.tsx` integrado ao Dashboard (substitui o seletor de data do dia); `AgendamentoForm` com checkbox de recorrência + frequência + duração; **`AgendamentoDetalhe`** (`/agenda/:id`) p/ desfazer; agenda com link no início + 🔁 nas séries. **105 unit tests** (+6), `tsc`+build OK, SQL 0008 renderizado.

**Code-review alto esforço (8 finders + verificação) → 10 achados + cortados APLICADOS:** (1) **cadência a partir do ÂNCORA** (`_ocorrencia(anchor,freq,k)`): mensal não deriva mais (31/01→28/02→31/03…); teste de regressão do drift; (2) **`desfazer` reescrito**: mantém a ocorrência ABERTA (vira avulsa), remove só as OUTRAS futuras 'agendado', **dissolve a série** (`serie_id`/`serie_frequencia`=NULL) — botão some depois, 2ª chamada dá `NaoRecorrente`; 1 DELETE (`rowcount`) + 1 UPDATE; (3) erro não-EXCLUSION na geração **para a série mas preserva** o primário + as criadas (não aborta a tx); (4/5) calendário: `useEffect` sincroniza o mês (conserta "Ir para hoje") + **mostra erro** do fetch; (6) **dashboard dividido** em `GET /dashboard/dia` e `/mes` (+ `pacientes` 1×) — clicar num dia não recomputa mais o mês/pacientes; (7) **frequência persistida** (`serie_frequencia`, migration 0008) → regra sobrevive p/ a Fase 8; (8) POST retorna **datas puladas** (`serie_pulados_datas`) e a SPA lista as lacunas; (9) rótulo **"Todo mês (mesma data)"** (mensal usa a data, não o dia da semana). **Cortados:** `fmtMesTitulo` → utils (dedup); `FREQUENCIAS` morto removido; hook **`useAcao`** extraído (FichaPaciente+AgendamentoDetalhe); resposta do router valida uma vez. **Aceitos/documentados:** DST na aritmética (Brasil sem horário de verão) e clamp inferior do calendário (degrada p/ zeros). **105 unit tests**, `tsc`+build OK, SQL 0008 (serie_id + serie_frequencia + índice) renderizado. → ✅ **commitada+pushada (`65d8a7b`). Aguarda deploy (`alembic upgrade head` → 0008).**

### 7g — Melhorias de UX (pedido do usuário, 2026-07-21)

**Objetivo:** polimento estético/UX (frontend-only, sem backend/migration). Pedidos: fonte maior p/ leitura; harmonia de espaçamento ("Agenda de hoje"/"Ver agenda →"); badge de contagem do calendário mais legível; redesenho da lista de Pacientes (estava vazia) com **espaço para observações da psicóloga**.

**Entregue:** fonte base ~18px (`html{font-size:112.5%}`, rem escala tudo); cabeçalhos de seção com respiro consistente + "Ver agenda →" como pílula discreta (`.cabecalho-secao a:not(.botao)`); calendário com badge maior ancorada na base da célula; **Pacientes como grade de cartões** (`PacienteCard.tsx`: avatar de iniciais, nome, idade·sexo·nascimento, situação, **observações editáveis inline** — grava via `PATCH /pacientes`, caixa de tamanho fixo `resize:none` + contador, sem backend novo). Helpers novos em `utils/format.ts` (`idadeEmAnos`, `iniciais`, `rotuloSexo`, `fmtMesTitulo`). **Preview visual publicado como artifact** p/ aprovação antes do deploy (padrão útil p/ tarefas estéticas).

**Code-review (3 finders) → 6 achados tratados:** `.cabecalho-secao a:not(.botao)`+`align:center` (conserta o botão "Nova evolução" que ficava acento-sobre-acento/invisível); `overflow-wrap` na observação; `rotuloSexo()` dedup (era duplicado na Ficha); `PacienteCard` usa `useAcao`; **nascimento de volta** na meta do cartão (desambigua homônimos); `idadeEmAnos` valida datas fora de faixa. **Aceito/documentado:** `obs` via `useState` fica stale só num futuro refetch (a lista não refaz fetch; o fix ingênuo quebraria o update otimista); célula do calendário não-quadrada em faixa estreita de largura (cosmético). `tsc`+build OK. → ✅ **commitada+pushada (`5603392`). Frontend-only: deploy = `up -d --build frontend` (sem migration).**

### 7h — Fluxo do calendário e organização do dashboard (pedido do usuário, 2026-07-21)

**Objetivo:** transformar o calendário em ponto de entrada para um novo agendamento e reduzir ruído visual no dashboard.

**Entregue:** clique em qualquer dia navega para `/agenda/novo?dia=AAAA-MM-DD`; o formulário valida o parâmetro e já carrega a ocupação da data. O bloco **Hoje** e a agenda de hoje ficam antes do calendário. O botão redundante "Novo agendamento" foi removido do dashboard. O histórico mensal ganhou seletores verticais de mês/ano e só consulta o backend ao clicar na lupa. **Pendências** aparecem antes de **Pacientes ativos/Responsáveis**. Frontend-only, sem migration. `tsc --noEmit` e `vite build` aprovados.

**Governança corrigida junto da 7h:** removidos endereços/credenciais/IDs operacionais do roadmap; rotação da credencial antes exposta marcada como obrigatória; embeddings `text-embedding-3-small` encerrados como decisão; README atualizado para React; estados obsoletos das seções 7b–7e reconciliados; retenção OpenAI separada entre garantia de código e evidência operacional obrigatória na Fase 9 (§3.4 #6).

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
- [ ] Confirmar elegibilidade/aprovação e ativação de **Zero Data Retention** no projeto/organização OpenAI; confirmar ausência de opt-in de treino; registrar projeto, modo efetivo, data e responsável, sem segredos (§3.4 #6). `store=false` sozinho não encerra esta tarefa.
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
> As linhas são cronológicas: estados 🟡 antigos documentam o momento da entrega e são substituídos pelas linhas ✅ mais recentes; o estado corrente vive no topo deste arquivo.

- 2026-07-21 — [Fase 7h/Docs] ✅ **UX do dashboard e saneamento de governança construídos, validados, commitados e enviados (`0ef55b1`).** Calendário→novo agendamento com data; Hoje antes do calendário; período mensal aplicado pela lupa; cadastros ativos depois das pendências; botão redundante removido. Credenciais/endereços/IDs removidos dos docs; rotação pendente no servidor; modelo de embedding encerrado; README e estados antigos reconciliados; verificação operacional de retenção OpenAI adicionada à Fase 9. `tsc` + build OK. **7f+7g+7h aguardam deploy.**
- 2026-07-21 — [Fase 7 e/f/g] ✅ **Commitadas+pushadas (`main` até `5603392`); 7f+7g aguardam deploy (servidor em `0007`).** **7e** (`e5b2d7c`): agenda por cliques + apagar; arquivar/apagar paciente (apagar bloqueado com prontuário, CFP §0.3); **evolução ↔ atendimento `realizado`** (migration `0007`); dashboard histórico dia/mês + cancelados + tooltips; responsável 18+. **7f** (`65d8a7b`): **calendário** no dashboard (dias coloridos; `/dashboard/{dia,mes,calendario}`) + **recorrência** de agendamento (série materializada `serie_id`/`serie_frequencia`, migration `0008`; cadência a partir do âncora; desfazer via `/agenda/:id`). **7g** (`5603392`): UX (fonte maior, espaçamento, badge do calendário, **cartões de paciente** com observações inline). Cada uma com code-review aplicado (7e:10, 7f:10, 7g:6). **Bug 7d resolvido no servidor:** "alterar nome → 500" era a migration `0006` não-aplicada (servidor estava em `0005`); `alembic upgrade head` aplicou 0006+0007. **Próximo: deploy 7f+7g (`up -d --build` + `alembic upgrade head` → 0008), depois Fase 8.**
- 2026-07-20 — [Fase 7d] 🟡 **Fechamento da Fase 7 construído + revisado + validado local (aguarda deploy).** 3 frentes: ações na agenda (realizado/falta/cancelar, backend já suportava), `GET /dashboard/resumo` (módulo novo sem migration, agregado sob RLS §2.1, 3 blocos de indicadores), configuração de perfil (`PATCH /auth/me` + `POST /auth/me/senha`, tela `/perfil`). Code-review alto esforço (8 finders) → **10 achados aplicados**, destaque: **migration `0006`** (GRANT UPDATE em `usuarios` — bloqueador de deploy), senha 72 **bytes**, e-mail minúsculo + login case-insensitive, **máquina de estados do agendamento no backend** (cancelado terminal; cancelar só de agendado), troca de e-mail exige senha atual + **auditoria** (`perfil_email_alterado`), TCLE com fonte única (`clausula_consentimento_ativo`), agenda sem refetch (overrides do retorno do PATCH), tile "hoje" coerente com a lista. 88 unit tests. **Deploy: `up -d --build backend frontend` + `alembic upgrade head` (0006).**
- 2026-07-17 — [Fase 0] Criados `arquitetura.md` (regras de ouro) e `planejamento_arquitetura.md` (este roadmap). Projeto ainda sem `git init`.
- 2026-07-17 — [Fase 0] Docs movidos para `docs/`. Estrutura rígida de diretórios criada: backend por domínio/módulo (`core/`, `db/`, `middleware/`, `api/`, `modules/` × 11 domínios), `frontend/`, `infra/`, `tests/`. Criados `.gitignore`, `.env.example`, `README.md`. **Decisão:** backend organizado por domínio/módulo (não por camada).
- 2026-07-17 — [Fase 0] `git init` (branch `main`), primeiro commit e push para `github.com/GA55555/projeto_agenda`. Falta `docker-compose.yml` (§1.1) + `postgresql.conf` (§1.2) + Dockerfiles para fechar a fase.
- 2026-07-20 — [Fase 7c] ✅ **Sub-fase Melhorias de Frontend CONCLUÍDA e validada no servidor.** Login→dashboard→cadastros percorridos no browser. **Hotfix pós-deploy:** `/auth/me` deu **500** porque `PerfilOut.email` era `EmailStr` e o validador rejeitou o TLD reservado `.local` na serialização da resposta → corrigido: response models (`Out`) usam `str`, `EmailStr` só na entrada. Commit `cbaebdf`.
- 2026-07-20 — [Fase 7c] 🟡 **Sub-fase Melhorias de Frontend construída+revisada+validada local (validar no servidor).** 7c.1 (design system clínico + sidebar + menu de perfil; `/auth/me`→nome/email), 7c.2 (cadastros: AgendamentoForm, Responsáveis lista/detalhe/form, **PacienteWizard**; backend: CPF dup→409), 7c.3 (**Dashboard** real como landing: stat tiles + agenda de hoje + ações, `allSettled`). Commits `8c7aa7c`/`4b89524`/(este). `tsc`+`build` OK; backend 61 unit tests. Pendências do dashboard (sem TCLE/embeddings) → futuro `GET /dashboard/resumo`.
- 2026-07-20 — [Fase 7] ✅ **CONCLUÍDA e validada no servidor (loop completo + RAG no browser).** Percorrido ponta a ponta via túnel SSH/Tailscale: login por cookie → agenda do dia → ficha (TCLE ativo) → Nova evolução → gerar rascunho (túnel opaco) → revisar/desanonimizar → aprovar/gravar. **RAG funcionando**: rascunhos seguintes trouxeram `chunks_contexto > 0` (histórico recuperado). Convergência Fases 4+5+6+7 provada; embeddings da Fase 5 populados/recuperados de fato. **Marco: backend + IA + frontend completos.** Restam Fases 8 (n8n/backups) e 9 (hardening).
- 2026-07-19 — [Fase 7b] 🟡 **Telas construídas + revisadas + validadas localmente (validar no servidor).** Frontend-only. Shell (nav Agenda·Pacientes·Sair); **Agenda do dia** (read-only, filtro [de,ate)); **Pacientes**; **Ficha** (TCLE ativo/revogado, responsáveis, evoluções, botão "Nova evolução" só com TCLE); **Editor** (loop IA: nota→`/llm/evolucoes/rascunho`→revisar/editar→aprovar→`/evolucoes`; trata 422/503/401). Cliente API estendido + tipos, hook `useAsync`, datas pt-BR. `tsc`+`build` OK. Code-review → 5 achados aplicados (422 mostra `detail` real; agenda-do-dia; ordena no BD; `allSettled` na ficha; confirma sobrescrita do rascunho). Decisões: landing=agenda-do-dia; agenda read-only; grava só a evolução editada; aprovação auditável (assinatura formal→§9).
- 2026-07-19 — [Fase 7a] ✅ **Deployada e validada no servidor.** SPA em `127.0.0.1:8090` (8080 é do Homarr); `COOKIE_SECURE=false` (HTTP). Provado: `GET /`→200 com CSP/headers; **login→/auth/me só com cookie httpOnly** devolveu o contexto do JWT via Nginx→backend (auth por cookie ponta a ponta, backend não-exposto). Healthcheck do BusyBox corrigido (`wget -q -O /dev/null`). Ver detalhe abaixo. ↓
- 2026-07-19 — [Fase 7a] 🟡 **Fundação da SPA construída + revisada + validada localmente.** **React + Vite + TS**; Nginx serve estáticos + proxy `/api`→backend (mesma origem, zero CORS, backend não-exposto §2.1.1), multi-stage 100 MB (§1.1). **Auth por cookie httpOnly** (login seta cookie; `get_current_user` lê cookie|bearer; `/auth/logout`); SPA com cliente `credentials:include` (JS não lê token), AuthContext via `/auth/me`, handler global de 401, telas Login+Home. Decisões: React; vertical slice; cookie httpOnly; só psicólogas. Backend 61 unit tests; frontend `build`+`tsc` OK. Code-review → 7 achados, 6 aplicados (COOKIE_SECURE default false, 401 global, erros diferenciados, logout espelha atributos, catch simplificado, npm ci); #4 mantido dual-mode. **Deploy exige `COOKIE_SECURE=false` no `.env` (HTTP).** Próxima: **7b (telas)**.
- 2026-07-19 — [Fase 6] ✅ **Concluída e validada no servidor.** Smoke com `OPENAI_API_KEY` ativa: `POST /llm/evolucoes/rascunho` → **200** com `evolucao` (evolução clínica coerente em pt, contextualizada) + `destaques` (3 alertas) + `chunks_contexto:0`. Provou contra a API viva: modo `json_object` (achado #2), sem 503 espúrio (achado #1), parse JSON→campos, desanonimização. Sem chave → 503 (fail-closed); campo errado → 422. **`OPENAI_API_KEY` agora ativa no servidor** (embeddings da Fase 5 também passam a preencher).
- 2026-07-19 — [Fase 6] 🟡 **Construída + revisada + validada localmente (validar no servidor).** Módulo `llm` stateless (sem migration): túnel completo `prompts.py`/`client.py`/`service.py`. Fluxo: gate TCLE §2.2 → RAG (`buscar_contexto`) → monta nota+histórico e **anonimiza numa passagem** (marcadores consistentes) → **guard-rail hard-abort** §3.4 → OpenAI (`gpt-4o-mini`, **sem tools**, `store=false`, timeout de chat) → **desanonimiza** → rascunho (evolução + destaques) p/ aprovação (Fase 7). Endpoint `POST /llm/evolucoes/rascunho`. Decisões: ambos deliverables (JSON); stateless; gpt-4o-mini; gate consentimento. Code-review alto esforço → **5 achados aplicados** (timeout de chat separado; "json" minúsculo p/ `json_object`; limpa marcadores residuais; `anonimizar_com_entidades` reusa entidades — otimiza Fase 5 tb; `SemConsentimentoAtivo` centralizada). **55 unit tests, 1 skip.**
- 2026-07-19 — [Fase 5] ✅ **Concluída e validada no servidor.** `alembic upgrade head` → `0005`. RLS FORCE nas 2 tabelas, `embedding vector(1536)`, **sem índice vetorial** (§3.1). Smoke API: gate §2.2 (TCLE revogado → **422**); criação → **201** com `total_chunks:2` e `embeddings_pendentes:2` (sem chave OpenAI → nota persiste, degradação graciosa). Paciente descartável com consentimento ativo usado para os testes da Fase 6, sem identificador versionado.
- 2026-07-19 — [Fase 5] 🟡 **Construída + revisada + validada localmente (validar no servidor).** IA Vetorial & RAG: tabelas `evolucoes` (nota crua sob RLS) + `evolucao_chunks` (`embedding vector(1536)`), migration `0005` (RLS+FORCE, FK composto, **sem índice vetorial** §3.1). `chunking.py` (parágrafo+frase c/ overlap), `embeddings.py` (OpenAI lazy §1.3 + canonicalização de marcadores + timeout), `service.py` (gate TCLE §2.2 + anonimiza→guard-rail→embeda §3.4 + retrieval híbrido §3.2). Endpoints `POST/GET /evolucoes`. **Decisões:** nota crua + embedding só anonimizado; síncrono c/ nota persistindo se OpenAI falhar (embedding pendente); gate de consentimento; sem LLM (Fase 6). Code-review alto esforço → **#1/#2/#4 aplicados** (timeout OpenAI; contagem via COUNT sem materializar vetor; grant sem DELETE). **42 unit tests, 1 skip.** Deps novas: `pgvector`, `openai`.
- 2026-07-19 — [Arquitetura] **Nova regra de ouro §3.4 "Superfície de ataque IA↔BD"** (constituição alterada, justificativa registada). Fixa 6 invariantes p/ a Fase 5/6: LLM sem tool/acesso ao BD; RAG sob RLS + filtro §3.2; **só vetorizar texto anonimizado** (embeddings são reversíveis); guard-rail em chat **e** embeddings; separação instrução/dado (anti prompt-injection); OpenAI retenção-zero. Checklist §5 atualizado. Motivada por pergunta do usuário sobre vazamento via prompts com BD compartilhado.
- 2026-07-19 — [Fase 4] ✅ **Concluída e validada no servidor.** Build com `[nlp]`+`pt_core_news_sm`. Smoke no container: round-trip exato, Pedro/CPF mascarados, guard-rail detecta vazamento, **NER prova mapeamento PER→PERSON** (`João Silva`→PERSON, `São Paulo`/`Belo Horizonte`→LOCATION — achado #3 resolvido). Modelo `sm` com recall menor é aceitável (NER é reforço; PII cadastrada cai no Aho-Corasick). `/health`→200. Sem migration nova.
- 2026-07-19 — [Fase 4] 🟡 **Construída + revisada + validada localmente.** Túnel opaco §2.3 como **módulo puro** (sem rota/tabela/migration — a não-persistência é a garantia da regra). Camadas: **Aho-Corasick puro** (`automaton.py`, offset via `_fold` que preserva comprimento), **regex ancorado** CPF/telefone/e-mail/CEP (`recognizers.py`), **NER Presidio+`pt_core_news_sm` lazy** atrás do extra `[nlp]`+flag (`nlp.py`). `sources.py` coleta PII cadastrada sob RLS; `pseudonimizador.py` = dicionário volátil só-RAM (`__repr__` não vaza) + round-trip exato; `guardrail.py` aborta se PII conhecida escapar. **Decisões:** cadastrado+NER; dicionário por requisição; módulo puro; modelo pequeno (§1.1). Code-review alto esforço → **5 achados aplicados** (offset caseless, O(n²), mapeamento NER, dep não usada, desempate). **35 unit tests passed, 1 skipped** (NER). Sem migration nova (última = `0004`).
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

- [x] **Framework do frontend:** **React + Vite + TS**. ✔ Resolvido 2026-07-19 (Fase 7a).
- [x] **Localização dos docs:** `docs/`. ✔ Resolvido 2026-07-17.
- [x] **Layout do backend:** por domínio/módulo. ✔ Resolvido 2026-07-17.
- [x] **Vínculo responsável↔paciente:** N:N (`vinculos_resp_paciente`). ✔ Resolvido 2026-07-18 (Fase 3).
- [x] **Auditoria:** log genérico append-only, imutabilidade no BD (REVOKE + trigger). ✔ Resolvido 2026-07-18. *Hash-chain fica como reforço futuro opcional (§2.2).*
- [x] **Provedor/modelo de embeddings:** OpenAI `text-embedding-3-small`, 1.536 dimensões. ✔ Resolvido e validado na Fase 5; mudar exige migration da coluna `vector(1536)`.
- [ ] Estratégia de rotação de segredos (Docker Secrets vs. `.env`). (Fase 0)

*Registre aqui toda decisão arquitetural que fugir do `arquitetura.md` e a justificativa.*
