# Agenda de Atendimentos

Gestão de agendamentos e prontuários psicológicos com foco em pacientes com
Transtorno do Espectro Autista (TEA). Self-hosted, hardware restrito, dados de
saúde de menores — conformidade **LGPD / ECA / CFP**.

> 📜 **Governança:** as regras inegociáveis vivem em
> [`docs/arquitetura.md`](./docs/arquitetura.md) (documento constitucional) e o
> roadmap executável em [`docs/planejamento_arquitetura.md`](./docs/planejamento_arquitetura.md).
> Em conflito entre conveniência e regra, **a regra prevalece**.

## Stack

- **Backend:** Python + FastAPI (Uvicorn, 2 workers)
- **Frontend:** SPA React + Vite + TypeScript servida por Nginx
- **Base de dados:** PostgreSQL + `pgvector`
- **Admin BD:** sem GUI — `psql` via `docker compose exec` (menor exposição, §2.1.1)
- **Automação:** n8n · **IA:** OpenAI (`text-embedding-3-small`)

## Estrutura do repositório

```
.
├── docs/                      # Governança (arquitetura + planejamento)
├── backend/
│   ├── app/
│   │   ├── core/              # config, security, logging (§1.3, §4.1)
│   │   ├── db/                # session, base, RLS (SET LOCAL — §2.1)
│   │   ├── middleware/        # injeção de tenant por transação (§2.1)
│   │   ├── api/               # router raiz /api/v1 + healthcheck
│   │   └── modules/           # domínios autocontidos:
│   │       ├── auth/  tenants/  responsaveis/  pacientes/
│   │       ├── consentimentos/  agendamentos/  evolucoes/  audit/
│   │       └── anonimizacao/  rag/  llm/  documentos/
│   ├── migrations/            # Alembic (Fase 1)
│   └── tests/                 # unit/ + integration/
├── frontend/                  # SPA + Nginx (Fase 7)
├── infra/
│   ├── postgres/              # postgresql.conf afinado + init/ (§1.2)
│   ├── secrets/               # Docker Secrets (fora do versionamento)
│   └── docker-compose.yml     # postgres, backend, frontend — com mem_limit (§1.1)
├── .env.example               # todas as variáveis (sem valores reais)
└── .gitignore
```

### Convenção de módulo de domínio

Cada pacote em `backend/app/modules/<dominio>/` segue o mesmo formato rígido:

| Arquivo | Responsabilidade |
| --- | --- |
| `router.py` | Rotas FastAPI do domínio |
| `models.py` | Modelos SQLAlchemy (tabela clínica → `tenant_id`, §2.1) |
| `schemas.py` | Schemas Pydantic (I/O da API) |
| `service.py` | Regras de negócio (sem acesso cross-tenant) |
| `dependencies.py` | Dependências FastAPI do domínio |
| `exceptions.py` | Exceções do domínio |

## Bootstrap no servidor (Debian 12)

Pré-requisitos no servidor: `git`, Docker Engine + plugin Compose v2.

```bash
# 1. Obter o repositório
git clone https://github.com/GA55555/projeto_agenda.git
cd projeto_agenda

# 2. Criar o .env (fora do versionamento) a partir do exemplo
cp .env.example .env

# 3. Gerar segredos fortes DIRETAMENTE no servidor e injetar no .env
PG_PW=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | cut -c1-32)
JWT=$(openssl rand -hex 32)
sed -i \
  -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${PG_PW}|" \
  -e "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=${JWT}|" \
  .env

# 4. Restringir o .env ao dono (§4.1)
chmod 600 .env

# 5. Subir (o .env fica na raiz; o compose em infra/ → usar --env-file)
cd infra
docker compose --env-file ../.env up --build -d

# 6. Verificar
docker compose ps                       # ambos healthy?
docker compose exec postgres psql -U agenda_admin -d agenda -c '\dx'   # extensão vector?
curl -s http://127.0.0.1:8000/health    # {"status":"ok"}
```

> Segredos são gerados **no próprio servidor** e nunca entram no git (`.env` está no `.gitignore`).

## Estado do projeto

Fase corrente e progresso: ver
[`docs/planejamento_arquitetura.md`](./docs/planejamento_arquitetura.md).
