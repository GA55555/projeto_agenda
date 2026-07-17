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
- **Frontend:** SPA (React/Vue — a decidir, Fase 7) servida por Nginx
- **Base de dados:** PostgreSQL + `pgvector`
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
│   │       └── anonimizacao/  rag/  llm/
│   ├── migrations/            # Alembic (Fase 1)
│   └── tests/                 # unit/ + integration/
├── frontend/                  # SPA + Nginx (Fase 7)
├── infra/
│   ├── postgres/              # postgresql.conf afinado + init/ (§1.2)
│   ├── secrets/               # Docker Secrets (fora do versionamento)
│   └── docker-compose.yml     # 3 serviços com mem_limit (§1.1)
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

## Bootstrap do ambiente local

> ⚠️ Passos completos serão preenchidos ao fim da Fase 0 (docker-compose +
> postgresql.conf). Rascunho do fluxo pretendido:

```bash
cp .env.example .env            # preencher segredos
# docker compose -f infra/docker-compose.yml up --build
```

## Estado do projeto

Fase corrente e progresso: ver
[`docs/planejamento_arquitetura.md`](./docs/planejamento_arquitetura.md).
