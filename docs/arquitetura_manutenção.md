# Manual de Arquitetura e Manutenção do `projeto_agenda`

> **Runbook operacional subordinado à Regra de Ouro.** Este documento descreve como
> manter, atualizar, verificar, copiar e recuperar o `projeto_agenda` sem romper as
> garantias de segurança, sigilo e isolamento definidas em
> [`arquitetura.md`](./arquitetura.md). Em caso de conflito, `arquitetura.md`
> prevalece. O roadmap e o estado real das entregas ficam em
> [`planejamento_arquitetura.md`](./planejamento_arquitetura.md).

**Versão do manual:** 1.0

**Data da revisão:** 2026-07-23

**Ambiente de referência:** Debian 12, Docker Compose v2, PostgreSQL 16/pgvector,
FastAPI, React/Nginx, SSD de 120 GB e HDD de 500 GB.

**Escopo:** manutenção técnica e proteção operacional de dados. Este manual não
substitui decisão clínica, orientação do CRP/CFP nem parecer jurídico sobre um caso
concreto.

---

## 1. Objetivo e regras que não podem ser quebradas

O sistema trata dados de saúde de crianças e adolescentes, documentos decorrentes de
avaliação psicológica e informações protegidas por sigilo profissional. Toda manutenção
deve preservar simultaneamente:

1. **Confidencialidade:** nenhuma pessoa, log, chamado, terminal remoto ou ferramenta de
   terceiros recebe conteúdo clínico sem necessidade, autorização e registro.
2. **Integridade:** banco, documentos e auditoria não podem ser alterados separadamente
   ou silenciosamente.
3. **Disponibilidade:** deve existir cópia recuperável e um procedimento ensaiado para
   voltar a operar.
4. **Autenticidade e rastreabilidade:** a origem de mudanças administrativas, uploads,
   downloads e incidentes deve permanecer identificável.
5. **Menor privilégio:** aplicação usa `agenda_app`, sujeito a RLS; superusuário é apenas
   *break-glass*.
6. **Menor exposição:** PostgreSQL não possui porta publicada; o frontend e o backend
   permanecem em `127.0.0.1`; não se cria console web de banco.
7. **Retenção responsável:** arquivar paciente não significa apagar prontuário. Não se
   elimina registro clínico ou backup por conveniência operacional.

### 1.1. Proibições operacionais

- Não copiar produção para notebook, ambiente de desenvolvimento ou serviço de IA.
- Não usar dados reais em testes; usar dados sintéticos e pacientes descartáveis.
- Não abrir PDF, DOCX ou imagem clínica para “ver se o backup funcionou”. Verificar
  hashes, metadados e restauração; inspeção de conteúdo exige necessidade clínica.
- Não publicar nomes, e-mails, CPFs, IDs, nomes originais de arquivos, tokens, IPs ou
  capturas do sistema em Git, chamados ou mensageria comum.
- Não executar `docker compose down -v`, `docker volume rm`, `docker system prune
  --volumes`, `DROP`, `TRUNCATE`, `alembic downgrade` ou restauração sobre produção sem
  autorização explícita, backup confirmado e plano de retorno.
- Não habilitar log de SQL/statements: consultas podem conter PII.
- Não editar arquivos diretamente dentro de `documentos_data`.
- Não montar o volume documental no Nginx nem expô-lo por servidor de arquivos.
- Não considerar RAID, snapshot, sincronização OneDrive ou o próprio SSD como backup.

---

## 2. Responsabilidades e registros fora do Git

Antes do uso em produção, o inventário operacional restrito deve nomear, sem entrar no
repositório:

| Papel | Responsabilidade mínima |
| --- | --- |
| Responsável técnica/psicóloga | decide acesso clínico, retenção excepcional, entrega ao titular e continuidade do cuidado |
| Controlador/representante | decide finalidade do tratamento e eventual comunicação à ANPD/titulares |
| Responsável operacional | executa manutenção, backup, restore, atualização e preservação de evidências |
| Contato de privacidade/encarregado, se designado | recebe solicitações de titulares e coordena incidentes LGPD |
| Substituto de emergência | acessa o cofre e o runbook quando o responsável principal estiver indisponível |

O inventário restrito deve guardar: host e localização física, caminho do repositório,
portas locais, contato dos responsáveis, localização das cópias, número de série dos
discos, data da última restauração, janela de manutenção, procedimento de acesso
Tailscale/SSH e localização do cofre de segredos. Ele **não** deve ficar no Git.

Cada manutenção gera um registro sem PII contendo: data/hora, executor, motivo, commit
anterior/novo, migration anterior/nova, backup usado, verificações, falhas e decisão de
retorno. Incidentes de dados pessoais têm registro próprio por pelo menos cinco anos.

---

## 3. Mapa operacional do sistema

> **Convenção dos comandos:** valores entre `<...>` são marcadores obrigatórios e
> precisam ser substituídos por caminhos/dispositivos do inventário restrito antes da
> execução. Nunca colar um comando contendo esses marcadores literalmente no shell.

| Ativo | Local lógico | Persistência | Observação |
| --- | --- | --- | --- |
| PostgreSQL | `/var/lib/postgresql/data` no contêiner | volume `pgdata` | dados clínicos, agenda, auditoria, hashes e metadados |
| Documentos | `/app/data/documentos` no backend | volume `documentos_data` | somente arquivos sanitizados; nomes internos opacos |
| Temporários de upload | `/tmp` no backend | `tmpfs` de 128 MiB | não deve sobreviver a restart |
| Configuração | repositório + `.env` | filesystem do host | `.env` é secreto, fora do Git, modo `0600` |
| Frontend | Nginx | imagem descartável | nunca contém documentos clínicos |
| Código/migrations | Git, branch `main` | remoto + clone do servidor | servidor apenas faz `git pull --ff-only` |
| Backup | HDD de 500 GB | repositório cifrado | não deve permanecer gravável/montado o tempo todo |

Os arquivos documentais seguem, dentro do backend:

```text
/app/data/documentos/<dois-caracteres>/<uuid-opaco>.pdf|docx|jpg|png
```

O nome apresentado à psicóloga e a relação paciente↔arquivo ficam no PostgreSQL. Por
isso, **um dump sem o volume ou um volume sem o dump não é um backup completo**.

### 3.1. Descobrir volumes e localização física

Executar de `infra/` no servidor:

```bash
docker compose --env-file ../.env config --volumes
```

```bash
docker inspect "$(docker compose --env-file ../.env ps -a -q backend)" --format '{{range .Mounts}}{{if eq .Destination "/app/data/documentos"}}volume={{.Name}} host={{.Source}}{{end}}{{end}}'
```

```bash
docker inspect "$(docker compose --env-file ../.env ps -a -q postgres)" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}volume={{.Name}} host={{.Source}}{{end}}{{end}}'
```

O campo `host=` é caminho administrativo *break-glass*. Não navegar, abrir ou alterar
seu conteúdo. O acesso rotineiro ocorre por API, `docker compose exec` ou ferramenta de
backup com montagem somente-leitura.

Quando for indispensável reconciliar nome exibido e chave opaca, a consulta abaixo usa
o superusuário e pode revelar PII no terminal. Executá-la somente em sessão privada, não
copiar a saída para chamados e registrar o acesso *break-glass*:

```bash
docker compose --env-file ../.env exec postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT nome_original, chave_armazenamento, pg_size_pretty(tamanho_bytes), criado_em FROM documentos_paciente ORDER BY criado_em DESC LIMIT 20;"'
```

---

## 4. Cadência de manutenção

### 4.1. A cada dia

- Confirmar que o backup terminou com código zero e que existe snapshot novo.
- Conferir `healthy`, reinícios inesperados, readiness, espaço livre e alertas de I/O.
- Confirmar que o HDD de backup não ficou montado/grávavel além da janela necessária.
- Registrar falha de backup no mesmo dia; dois backups diários consecutivos ausentes
  constituem incidente operacional alto.

```bash
cd <CAMINHO_RESTRITO_DO_REPOSITORIO>/infra
```

```bash
docker compose --env-file ../.env ps
```

```bash
curl --fail --silent http://127.0.0.1:8010/health
```

```bash
curl --fail --silent http://127.0.0.1:8010/health/ready
```

```bash
df -h / /var/lib/docker <PONTO_DE_MONTAGEM_DO_HDD>
```

```bash
docker system df
```

### 4.2. A cada semana

- Ler logs de erro sem exportá-los e sem habilitar corpo de requisição/SQL.
- Verificar uso dos volumes, memória, reinícios e eventos de OOM.
- Verificar saúde SMART de SSD e HDD.
- Executar verificação estrutural do repositório de backup.
- Rever usuários afastados/desligados e suspender acesso imediatamente.

```bash
docker compose --env-file ../.env logs --since 168h --no-color backend postgres frontend
```

```bash
docker stats --no-stream agenda_postgres agenda_backend agenda_frontend
```

```bash
docker inspect -f '{{.Name}} reinicios={{.RestartCount}} oom={{.State.OOMKilled}} status={{.State.Status}}' agenda_postgres agenda_backend agenda_frontend
```

```bash
sudo smartctl -H -A <DISPOSITIVO_SSD>
```

```bash
sudo smartctl -H -A <DISPOSITIVO_HDD>
```

```bash
restic --repository-file <ARQUIVO_REPOSITORY> --password-file <ARQUIVO_PASSWORD> check
```

### 4.3. A cada mês

- Aplicar atualizações de segurança em janela controlada, após backup e testes.
- Rever dependências Python, Node, imagens Docker e notas de segurança dos fabricantes.
- Conferir migrations, RLS/FORCE, privilégios do role da aplicação e imutabilidade da
  auditoria.
- Conferir crescimento do banco e do volume documental.
- Fazer restore técnico isolado de uma cópia recente.
- Ler 10% dos pacotes do backup com `restic check --read-data-subset=10%`; alternar as
  execuções até cobrir regularmente o conjunto e executar leitura integral trimestral.
- Rever falhas de login, downloads anormais e operações *break-glass* sem consultar
  conteúdo clínico.

### 4.4. A cada trimestre

- Fazer ensaio completo de desastre em ambiente isolado: banco + documentos + aplicação.
- Executar `restic check --read-data` fora do horário de atendimento.
- Rever o plano de incidente e fazer exercício de mesa com responsável técnica,
  controlador e responsável operacional.
- Testar acesso do substituto ao runbook e ao cofre, sem revelar segredos no registro.
- Rever RPO/RTO, capacidade do SSD/HDD e necessidade de segundo meio/off-site.
- Confirmar configurações de retenção/treino/ZDR do projeto OpenAI conforme a Regra de
  Ouro; `store=false` no código, isoladamente, não comprova ZDR.

### 4.5. A cada ano ou após mudança relevante

- Revisar LGPD, atos da ANPD, resoluções CFP/CRP e contratos com operadores.
- Revalidar inventário de tratamento, bases legais, TCLE e canal dos titulares.
- Rever prazo de guarda caso a caso com a responsável técnica.
- Rotacionar segredos conforme risco e imediatamente quando houver suspeita de exposição.
- Revisar este manual após mudança de infraestrutura, formato documental, autenticação,
  backup, IA, legislação ou responsável operacional.

---

## 5. Capacidade, desempenho e prevenção de saturação

### 5.1. Limites atuais obrigatórios

| Recurso | Limite atual |
| --- | --- |
| PostgreSQL | 1,5 GB RAM |
| Backend | 1,0 GB RAM |
| Frontend | 100 MB RAM |
| Upload individual | 20 MiB |
| Cota documental por tenant | 2 GiB |
| Temporários de upload | 128 MiB em RAM (`tmpfs`) |
| Sanitização | uma por vez entre workers, timeout de 35 s |

```bash
docker compose --env-file ../.env exec backend python -c "from app.core.config import settings as s; print('arquivo=', s.documentos_tamanho_max_bytes, 'cota=', s.documentos_cota_tenant_bytes, 'timeout=', s.documentos_sanitizacao_timeout_seconds)"
```

```bash
docker compose --env-file ../.env exec backend du -sh /app/data/documentos
```

```bash
docker compose --env-file ../.env exec postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT pg_size_pretty(pg_database_size(current_database()));"'
```

```bash
docker compose --env-file ../.env exec postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT count(*) AS arquivos, pg_size_pretty(coalesce(sum(tamanho_bytes),0)) AS tamanho FROM documentos_paciente;"'
```

### 5.2. Faixas de atuação do armazenamento

| Uso do SSD | Ação |
| --- | --- |
| abaixo de 70% | normal; acompanhar tendência |
| 70–79% | aviso; identificar crescimento e planejar capacidade |
| 80–84% | crítico; suspender tarefas pesadas, investigar imediatamente |
| 85% ou mais | emergência; bloquear novos uploads se necessário e preservar espaço para PostgreSQL/SO |

Manter aproximadamente 20% livre reduz risco de falha de banco, falta de espaço para
WAL, builds e operações temporárias. Não liberar espaço apagando volumes. Primeiro
identificar a origem com `df`, `du` e `docker system df -v`. Imagens sem uso só podem ser
removidas depois de confirmar que não são necessárias para retorno; volumes nunca entram
em limpeza genérica.

### 5.3. PostgreSQL

Autovacuum permanece ativo. Não executar rotineiramente `VACUUM FULL` ou `REINDEX`:
essas operações podem bloquear tabelas, consumir I/O e exigir espaço adicional.

```bash
docker compose --env-file ../.env exec postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT relname,n_live_tup,n_dead_tup,last_autovacuum,last_autoanalyze FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;"'
```

```bash
docker compose --env-file ../.env exec postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT datname,numbackends,xact_commit,xact_rollback,deadlocks,temp_bytes FROM pg_stat_database WHERE datname=current_database();"'
```

Se houver bloat, lentidão ou deadlocks recorrentes, diagnosticar antes de agir. Uma
manutenção extraordinária deve ter backup, estimativa de espaço, janela e retorno.

---

## 6. Política de backup

### 6.1. Objetivos operacionais

- **RPO inicial:** até 24 horas para o conjunto coordenado banco + documentos.
- **RTO inicial:** até 4 horas para restauração em hardware funcional.
- **Frequência:** diária; backup adicional antes de migration, atualização relevante ou
  manutenção destrutiva.
- **Retenção operacional sugerida:** 14 diários, 8 semanais e 3 mensais, sujeita à
  capacidade e à política de eliminação aprovada.
- **Validação:** estrutura semanal, amostra de dados mensal e restauração completa
  trimestral.

RPO/RTO são metas iniciais, não garantia. O arquivamento contínuo de WAL previsto na
Fase 8 pode reduzir perda do banco, mas o ponto de restauração clínico completo continua
dependendo da coerência com `documentos_data`.

### 6.2. Regra 3-2-1 e limitação atual

O alvo é manter três cópias, em dois meios, com uma cópia offline ou fora do local. SSD
+ HDD no mesmo servidor/local **não satisfaz completamente** essa regra: incêndio,
furto, sobretensão ou ransomware pode atingir ambos. O mínimo recomendado é:

1. produção no SSD;
2. repositório Restic cifrado no HDD, conectado/montado só durante backup/verificação;
3. segunda cópia cifrada em disco removível guardado em outro local, ou serviço remoto
   contratado e avaliado sob LGPD.

O segredo do repositório Restic deve ter cópia offline no cofre. Sem ele, backup cifrado
é irrecuperável. Ele não deve ficar apenas no mesmo servidor nem dentro do próprio
repositório.

### 6.3. Conteúdo obrigatório de cada conjunto

- dump lógico PostgreSQL em formato custom (`pg_dump -Fc`);
- globals/roles (`pg_dumpall --globals-only`), protegidos como segredo;
- arquivo do volume `documentos_data`;
- manifestos SHA-256 do dump, globals e arquivo documental;
- commit Git, migration atual, versão PostgreSQL e data/hora UTC;
- `docker-compose.yml`, `postgresql.conf` e `.env`, estes dentro do repositório cifrado;
- bundle das imagens Docker aprovadas a cada versão implantada, enquanto backend e
  imagens-base não estiverem integralmente fixados por lockfiles e digests;
- quando a Fase 8 ativar automações: backup consistente do n8n, sua chave de criptografia,
  workflows, credenciais cifradas, versão e eventual armazenamento binário;
- relatório sem PII da execução.

O commit atual **não reconstrói sozinho uma imagem idêntica**: o backend usa intervalos de
versão, não possui lockfile completo, baixa o modelo spaCy durante o build e as imagens-base
usam tags mutáveis. Até isso ser corrigido, exportar as imagens aprovadas após cada deploy
e guardá-las cifradas como artefato de recuperação. Não incluir caches, `node_modules`,
`dist`, temporários ou logs com PII.

### 6.4. Backup manual coordenado — procedimento de contingência

> **Estado atual:** este procedimento é o baseline manual. A automação Restic + WAL +
> alertas ainda pertence à Fase 8. O diretório de estágio precisa estar em filesystem
> cifrado; caso o HDD não use criptografia de bloco, não deixar dumps/tar em texto claro.

1. Avisar a janela e confirmar que ninguém está registrando atendimento.
2. Verificar espaço e saúde dos contêineres.
3. Criar diretório de execução com permissão `0700` e `umask 077`.
4. Parar frontend e backend; manter PostgreSQL ativo para o dump consistente.
5. Gerar dump, globals e arquivo somente-leitura do volume documental.
6. Gerar checksums e metadados do conjunto.
7. Reiniciar o serviço mesmo se uma etapa de backup falhar.
8. Verificar os artefatos; só então enviar ao repositório Restic cifrado.
9. Confirmar snapshot novo e remover o estágio conforme a política do filesystem cifrado.

```bash
cd <CAMINHO_RESTRITO_DO_REPOSITORIO>/infra
```

```bash
umask 077
```

```bash
export BACKUP_RUN=<PONTO_CIFRADO_DE_ESTAGIO>/$(date -u +%Y%m%dT%H%M%SZ)
```

```bash
mkdir -p "$BACKUP_RUN"
```

```bash
docker compose --env-file ../.env stop frontend backend
```

```bash
docker compose --env-file ../.env exec -T postgres sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$BACKUP_RUN/agenda.dump"
```

```bash
docker compose --env-file ../.env exec -T postgres sh -lc 'pg_dumpall -U "$POSTGRES_USER" --globals-only' > "$BACKUP_RUN/globals.sql"
```

```bash
export DOCS_VOLUME=$(docker inspect "$(docker compose --env-file ../.env ps -a -q backend)" --format '{{range .Mounts}}{{if eq .Destination "/app/data/documentos"}}{{.Name}}{{end}}{{end}}')
```

```bash
test -n "$DOCS_VOLUME"
```

```bash
docker run --rm -v "$DOCS_VOLUME:/source:ro" -v "$BACKUP_RUN:/backup" nginx:1.27-alpine tar -C /source -cf /backup/documentos.tar .
```

```bash
git rev-parse HEAD > "$BACKUP_RUN/git-commit.txt"
```

```bash
date -u +%Y-%m-%dT%H:%M:%SZ > "$BACKUP_RUN/criado-em-utc.txt"
```

```bash
docker compose --env-file ../.env exec -T postgres postgres --version > "$BACKUP_RUN/postgres-version.txt"
```

```bash
docker compose --env-file ../.env run --rm --no-deps backend alembic current > "$BACKUP_RUN/alembic-current.txt"
```

```bash
sha256sum "$BACKUP_RUN/agenda.dump" "$BACKUP_RUN/globals.sql" "$BACKUP_RUN/documentos.tar" > "$BACKUP_RUN/SHA256SUMS"
```

```bash
docker compose --env-file ../.env start backend frontend
```

```bash
docker compose --env-file ../.env exec -T postgres pg_restore --list < "$BACKUP_RUN/agenda.dump" > /dev/null
```

```bash
tar -tf "$BACKUP_RUN/documentos.tar" > /dev/null
```

```bash
sha256sum --check "$BACKUP_RUN/SHA256SUMS"
```

```bash
restic --repository-file <ARQUIVO_REPOSITORY> --password-file <ARQUIVO_PASSWORD> backup "$BACKUP_RUN" ../.env docker-compose.yml postgres/postgresql.conf --tag agenda-coordenado --group-by host,tags
```

```bash
restic --repository-file <ARQUIVO_REPOSITORY> --password-file <ARQUIVO_PASSWORD> snapshots --latest 1
```

Se o dump ou o `tar` falhar, o conjunto é inválido. Reiniciar o serviço, preservar o log
sem dados clínicos, corrigir a causa e repetir com outro diretório. Nunca misturar
artefatos de execuções diferentes.

#### 6.4.1. Bundle das imagens aprovadas — após cada versão implantada

Enquanto os builds não forem integralmente reproduzíveis, salvar as três imagens que
estão efetivamente em execução. O bundle não precisa ser recriado no backup diário; criar
um novo quando qualquer imagem mudar e mantê-lo no Restic com tag própria.

```bash
export IMAGE_BUNDLE_DIR=<PONTO_CIFRADO_DE_ESTAGIO>/imagens-$(git rev-parse --short=12 HEAD)
```

```bash
mkdir -p "$IMAGE_BUNDLE_DIR"
```

```bash
docker image save "$(docker inspect -f '{{.Config.Image}}' agenda_postgres)" "$(docker inspect -f '{{.Config.Image}}' agenda_backend)" "$(docker inspect -f '{{.Config.Image}}' agenda_frontend)" > "$IMAGE_BUNDLE_DIR/imagens-docker.tar"
```

```bash
git rev-parse HEAD > "$IMAGE_BUNDLE_DIR/git-commit.txt"
```

```bash
sha256sum "$IMAGE_BUNDLE_DIR/imagens-docker.tar" > "$IMAGE_BUNDLE_DIR/SHA256SUMS"
```

```bash
restic --repository-file <ARQUIVO_REPOSITORY> --password-file <ARQUIVO_PASSWORD> backup "$IMAGE_BUNDLE_DIR" --tag agenda-imagens --group-by host,tags
```

No host limpo de recuperação, validar o checksum antes de carregar:

```bash
docker image load -i "$IMAGE_BUNDLE_DIR/imagens-docker.tar"
```

### 6.5. Retenção e limpeza do repositório

O diretório `$BACKUP_RUN` muda a cada execução. Sem `--group-by host,tags`, o Restic
separaria cada caminho datado em um grupo e a retenção não removeria snapshots antigos.
Usar o mesmo agrupamento no `backup` e no `forget`.

Primeiro simular; depois revisar a lista antes de remover snapshots. `prune` exige acesso
de exclusão e deve rodar com credencial administrativa separada quando houver modo
append-only.

```bash
restic --repository-file <ARQUIVO_REPOSITORY> --password-file <ARQUIVO_ADMIN_PASSWORD> forget --tag agenda-coordenado --group-by host,tags --keep-daily 14 --keep-weekly 8 --keep-monthly 3 --dry-run
```

```bash
restic --repository-file <ARQUIVO_REPOSITORY> --password-file <ARQUIVO_ADMIN_PASSWORD> forget --tag agenda-coordenado --group-by host,tags --keep-daily 14 --keep-weekly 8 --keep-monthly 3 --prune
```

Backup não é arquivo histórico. O prontuário exigido por norma permanece no sistema ou
em arquivo clínico controlado pelo prazo aplicável; snapshots operacionais expiram para
reduzir exposição e tornar eliminações futuras tecnicamente administráveis.

### 6.6. WAL/PITR — alvo da Fase 8, não ativo hoje

`pg_dump` é backup lógico e **não** participa de PITR. Para PITR são necessários
`archive_mode`, `archive_command`/ferramenta equivalente, base backup e sequência
contínua de WAL. Antes de ativar:

- definir ferramenta e diretório cifrado;
- criar base backup e testar recuperação;
- monitorar `pg_stat_archiver`, `failed_count` e crescimento de `pg_wal`;
- manter WAL necessário à base válida;
- evitar `archive_timeout` agressivo no hardware restrito;
- incluir configurações PostgreSQL no backup, pois WAL não as restaura;
- documentar a linha do tempo e o ponto escolhido para recuperação.

Falha de arquivamento pode lotar o SSD. Não ativar WAL archiving sem alerta de espaço e
ensaio de restore.

### 6.7. n8n — requisito para ativar a Fase 8

O n8n já existe no servidor, mas ainda não integra o `projeto_agenda`. Antes de ativar o
primeiro workflow, registrar no inventário restrito: método de instalação, versão, banco,
volumes, modo de armazenamento binário, `N8N_ENCRYPTION_KEY` e responsável pelas
credenciais OAuth. A chave não entra no Git e precisa de cópia offline no cofre.

O backup coordenado da Fase 8 deve:

1. pausar novas execuções e aguardar as ativas terminarem;
2. copiar consistentemente o banco e o armazenamento binário do n8n;
3. preservar a mesma `N8N_ENCRYPTION_KEY`, sem a qual credenciais cifradas podem ficar
   inutilizáveis;
4. registrar a versão da imagem e exportar workflows como evidência adicional — exportar
   JSON sozinho não substitui banco, credenciais e chave;
5. restaurar em instância isolada, com webhooks, e-mail, Drive e demais integrações
   desabilitados;
6. só reativar automações depois de testar autenticação do webhook e destino dos dados.

O procedimento exato depende do banco/volumes da instalação n8n já existente e deve ser
escrito e ensaiado antes da Fase 8 sair de “pendente”. Não presumir que o backup deste
Compose inclui um serviço hospedado fora dele.

---

## 7. Restauração e recuperação de desastre

### 7.1. Princípios

- **Restore não é comprovado por checksum:** checksum prova que a cópia não mudou;
  somente uma restauração prova usabilidade.
- Ensaiar em volumes e contêineres isolados, sem publicar portas e sem acesso de usuários.
- Nunca restaurar um dump e documentos de datas diferentes.
- Nunca conectar um restore de produção à OpenAI, n8n, e-mail ou Drive.
- Em incidente suspeito, preservar o ambiente original e restaurar em host limpo.
- Registrar início, snapshot, resultados, contagens e tempo total sem PII.

### 7.2. Verificação técnica mensal

1. Restaurar o snapshot Restic em diretório temporário protegido.
2. Validar `SHA256SUMS`, catálogo do dump e catálogo do tar.
3. Subir PostgreSQL 16/pgvector isolado, sem porta publicada.
4. Restaurar globals em cluster novo quando for ensaio completo; para teste lógico
   mensal, usar `--no-owner --no-privileges` e registrar que isso não valida roles.
5. Restaurar os documentos em volume isolado.
6. Comparar quantidade/tamanho do banco com arquivos, validar hashes e testar download
   por API em ambiente sem integrações externas.
7. Destruir o ambiente de teste de forma controlada após o relatório.

Qualquer erro de checksum, `pg_restore`, RLS, hash documental ou arquivo ausente torna o
backup não confiável e abre incidente operacional.

### 7.3. Recuperação de produção

1. Declarar indisponibilidade e impedir novas escritas.
2. Identificar causa; se houver comprometimento, isolar rede e não reutilizar host/segredo.
3. Selecionar o último conjunto coordenado íntegro anterior ao evento.
4. Provisionar Debian/Docker suportados e volumes novos.
5. Restaurar roles/globals, depois `agenda.dump`.
6. Restaurar `documentos.tar` no volume novo, preservando caminhos e permissões.
7. Recuperar `.env` pelo cofre/backup cifrado; rotacionar credenciais se houver suspeita.
8. Fazer checkout do commit registrado e construir imagens.
9. Confirmar migration, RLS/FORCE, role `agenda_app`, auditoria e hashes documentais.
10. Subir sem integrações externas; executar smoke tests com dados sintéticos.
11. Liberar acesso somente após aprovação técnica e da responsável.
12. Monitorar intensivamente e produzir relatório pós-incidente.

Não executar `alembic downgrade` para “combinar” um dump. O código deve ser restaurado
ao commit do conjunto; migrations posteriores só são aplicadas depois que a base
restaurada estiver validada.

### 7.4. Template técnico para ambiente novo e vazio

> **Nunca apontar estes comandos para os volumes de produção.** O diretório de recovery,
> projeto Compose e volumes devem ser novos. Como o Compose atual fixa `container_name`,
> este template exige **host/VM separado e limpo**, sem os contêineres de produção. Antes
> de prosseguir, conferir visualmente os nomes retornados por `docker compose
> config --volumes` e `docker volume ls`.

Escolher explicitamente o snapshot coordenado e inspecionar sua árvore antes de restaurar:

```bash
export SNAPSHOT_ID=<ID_DO_SNAPSHOT_COORDENADO>
```

```bash
restic --repository-file <ARQUIVO_REPOSITORY> --password-file <ARQUIVO_PASSWORD> ls "$SNAPSHOT_ID"
```

```bash
export RESTORE_TARGET=<DIRETORIO_PROTEGIDO_E_VAZIO>
```

```bash
restic --repository-file <ARQUIVO_REPOSITORY> --password-file <ARQUIVO_PASSWORD> restore "$SNAPSHOT_ID" --target "$RESTORE_TARGET"
```

O Restic preserva a árvore dos caminhos de origem dentro do `--target`. Localizar nos
resultados de `restic ls` o diretório datado que contém `SHA256SUMS` e defini-lo, sem
presumir que os arquivos estarão na raiz do target:

```bash
export RESTORE_RUN=<CAMINHO_RESTAURADO_QUE_CONTEM_SHA256SUMS>
```

```bash
cd "$RESTORE_RUN"
```

```bash
sha256sum --check SHA256SUMS
```

Em um clone novo do repositório, usar exatamente o commit registrado:

```bash
git checkout --detach "$(cat "$RESTORE_RUN/git-commit.txt")"
```

Restaurar também o snapshot `agenda-imagens` correspondente ao mesmo commit, validar seu
`SHA256SUMS` e carregar as imagens aprovadas. Os nomes estáveis `agenda-backend` e
`agenda-frontend` do Compose fazem o recovery reutilizar o conteúdo carregado:

```bash
docker image load -i <DIRETORIO_DO_BUNDLE_VALIDADO>/imagens-docker.tar
```

Recuperar `.env` do snapshot cifrado para a raiz do clone, revisar host/portas, zerar
`OPENAI_API_KEY`, `N8N_WEBHOOK_URL` e `N8N_WEBHOOK_TOKEN` no ensaio e impedir qualquer
integração externa. Em seguida:

```bash
chmod 600 .env
```

```bash
cd infra
```

```bash
docker compose --project-name agenda_restore --env-file ../.env up -d --wait --wait-timeout 120 postgres
```

```bash
docker compose --project-name agenda_restore --env-file ../.env ps
```

O bootstrap do cluster novo recria os roles configurados. `globals.sql` contém hashes de
senha e serve para conferir roles adicionais; não o aplicar cegamente sobre roles já
criados. Depois da revisão:

```bash
docker compose --project-name agenda_restore --env-file ../.env exec -T postgres sh -lc 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --exit-on-error' < "$RESTORE_RUN/agenda.dump"
```

Criar o backend parado para materializar um **novo** volume documental e descobrir seu
nome:

```bash
docker compose --project-name agenda_restore --env-file ../.env create backend
```

```bash
export RESTORE_DOCS_VOLUME=$(docker inspect "$(docker compose --project-name agenda_restore --env-file ../.env ps -a -q backend)" --format '{{range .Mounts}}{{if eq .Destination "/app/data/documentos"}}{{.Name}}{{end}}{{end}}')
```

```bash
test -n "$RESTORE_DOCS_VOLUME"
```

Confirmar que o volume é novo e vazio antes da extração:

```bash
docker run --rm -v "$RESTORE_DOCS_VOLUME:/target:ro" nginx:1.27-alpine sh -lc 'test -z "$(find /target -mindepth 1 -maxdepth 1 -print -quit)"'
```

```bash
docker run --rm -i -v "$RESTORE_DOCS_VOLUME:/target" nginx:1.27-alpine tar -C /target -xf - < "$RESTORE_RUN/documentos.tar"
```

Subir sem exposição externa, confirmar migration e executar as validações da seção 7.2:

```bash
docker compose --project-name agenda_restore --env-file ../.env up -d backend frontend
```

```bash
docker compose --project-name agenda_restore --env-file ../.env exec backend alembic current
```

Se a restauração for um ensaio, as portas do `.env` devem ser diferentes e ainda presas
a `127.0.0.1`. Se for recuperação real, só trocar o tráfego para o novo ambiente após
aprovação e smoke tests; o ambiente anterior continua preservado.

---

## 8. Atualização e deploy seguro

### 8.1. Pré-condições

- janela aprovada e usuários avisados;
- `main` limpa no servidor, sem commit local;
- revisão do diff, migrations e novas variáveis;
- testes locais aprovados;
- backup coordenado recente verificado;
- espaço para build e retorno;
- commit anterior e migration anterior anotados.

```bash
git status --short
```

```bash
git fetch origin
```

```bash
git log --oneline --decorate HEAD..origin/main
```

```bash
git diff --stat HEAD..origin/main
```

### 8.2. Testes antes do deploy

No ambiente de desenvolvimento com Python 3.12 e dependências `[dev]`:

```bash
cd backend
```

```bash
python -m compileall -q app tests migrations
```

```bash
python -m ruff check app tests migrations
```

```bash
python -m pytest tests/unit
```

```bash
python -m pip check
```

No frontend:

```bash
cd ../frontend
```

```bash
npx tsc --noEmit
```

```bash
npm run build
```

Testes de integração precisam do PostgreSQL de teste. Nunca apontar `DATABASE_URL` de
teste para produção.

### 8.3. Deploy

De `infra/`, depois do backup:

```bash
git pull --ff-only origin main
```

```bash
docker compose --env-file ../.env build backend frontend
```

```bash
docker compose --env-file ../.env stop frontend backend
```

```bash
docker compose --env-file ../.env run --rm --no-deps backend alembic upgrade head
```

```bash
docker compose --env-file ../.env up -d backend frontend
```

```bash
docker compose --env-file ../.env ps
```

```bash
docker compose --env-file ../.env exec backend alembic current
```

```bash
curl --fail --silent http://127.0.0.1:8010/health/ready
```

Validar pelo frontend: login, dashboard, agenda, ficha, histórico e lista/download de um
documento sintético. Não fazer upload de arquivo clínico apenas para smoke test.

### 8.4. Falha e retorno

- Falha antes da migration: manter serviço anterior, corrigir build/configuração.
- Falha transacional da migration: confirmar `alembic current` e logs; não improvisar SQL.
- Migration aplicada com app incompatível: interromper acesso. A opção segura pode ser
  corrigir para frente ou restaurar o conjunto coordenado em volumes novos.
- Não reapontar volumes até validar a recuperação.
- Não apagar imagens/volume antigos durante a janela de observação.

Todo rollback de dados é uma restauração e requer autorização porque descarta alterações
posteriores ao ponto escolhido.

---

## 9. Manutenção de segurança

### 9.1. Segredos

- `.env` sempre fora do Git e `chmod 600`.
- Senhas únicas para `agenda_admin`, `agenda_app`, JWT, n8n, OpenAI e Restic.
- Não exibir `.env` com `cat`, não colar em chat e não registrar valor em histórico shell.
- Rotação por suspeita é imediata; rotação programada deve considerar sessões JWT,
  `DATABASE_URL`, role PostgreSQL, webhook e reinício coordenado.
- Guardar recuperação Restic e acesso de emergência em cofre offline com substituto.
- A migração futura para Docker Secrets deve manter compatibilidade explícita no código;
  apenas criar arquivos em `infra/secrets` não altera o carregamento atual.

### 9.2. Acessos

- Uma conta por psicóloga; nunca compartilhar senha.
- Remover/suspender acesso no mesmo dia do desligamento ou afastamento.
- Revisar mensalmente contas e papéis.
- Acesso administrativo via SSH/Tailscale e `docker compose exec`; PostgreSQL sem porta.
- Registrar toda abertura *break-glass*. Consultas administrativas cruzam RLS quando
  usam superusuário e, portanto, são excepcionalmente sensíveis.
- MFA deve existir no acesso ao servidor/Tailscale e nos provedores externos. MFA da
  aplicação ainda é pendência de hardening e deve constar no risco de go-live.

Para suspender uma conta, executar de `infra/` e registrar a operação no inventário
restrito. A API confere `usuarios.ativo` em toda requisição autenticada, portanto a
suspensão também revoga JWTs já emitidos:

```bash
docker compose --env-file ../.env exec backend python -m app.cli suspender-usuario --email <EMAIL_DA_CONTA>
```

Reativação exige autorização equivalente:

```bash
docker compose --env-file ../.env exec backend python -m app.cli reativar-usuario --email <EMAIL_DA_CONTA>
```

### 9.3. Patches e vulnerabilidades

1. Ler avisos de Debian, Docker, PostgreSQL, Python, Node/Nginx e bibliotecas de documento.
2. Priorizar vulnerabilidade explorada ou que afete parser de PDF/DOCX/imagem, auth,
   FastAPI, banco ou proxy.
3. Atualizar locks/dependências em mudança própria, revisar changelog e executar toda a
   suíte.
4. Reconstruir imagens; não instalar pacote manual dentro de contêiner em produção.
5. Fazer backup antes de atualização do SO/Docker/PostgreSQL.
6. Reboot controlado quando necessário; verificar todos os serviços pré-existentes.

Atualização de major do PostgreSQL exige plano específico de `pg_upgrade` ou dump/restore,
ensaio e tempo de indisponibilidade. Nunca trocar apenas a tag da imagem sobre o mesmo
volume.

### 9.4. Logs e evidências

- Logs não devem conter corpo clínico, tokens, headers de autenticação ou SQL.
- Acesso a logs é administrativo; exportações são minimizadas e cifradas.
- Ajustar retenção para não lotar o SSD; não apagar logs ligados a incidente.
- Sincronizar horário do host; registrar eventos em UTC e apresentar fuso local quando
  necessário.
- Preservar evidência por cópia somente-leitura e hash; trabalhar sobre cópia.

---

## 10. Protocolos de manutenção de dados de saúde e prontuário

### 10.1. Guarda e separação clínica

A Resolução CFP nº 1/2009 determina registro documental atualizado, organizado,
sigiloso e guardado em local que assegure privacidade, por no mínimo cinco anos. A
Resolução CFP nº 6/2019 aplica prazo mínimo de cinco anos aos documentos escritos e ao
material que os fundamenta, físico ou digital. Prazo pode ser ampliado por lei, ordem
judicial ou necessidade específica.

Consequências para o projeto:

- paciente arquivado continua protegido e retido;
- documentos de testes e instrumentos ficam em acesso exclusivo da psicóloga;
- administrador técnico verifica metadados/hashes, não conteúdo;
- cópia entregue a responsável/titular segue decisão da psicóloga, validação de
  identidade/guarda e protocolo de entrega; não é tarefa automática do mantenedor;
- correção de cadastro não autoriza reescrever evolução clínica histórica;
- litígio, fiscalização ou ordem judicial suspende eliminação relacionada (*legal hold*);
- encerramento da clínica exige plano formal de custódia/destinação, não exclusão em massa.

### 10.2. Retenção, arquivamento e eliminação

1. Registrar a categoria, data inicial do prazo e fundamento de retenção.
2. Manter prontuário por no mínimo cinco anos, salvo prazo maior aplicável.
3. Antes de eliminar, confirmar ausência de ordem judicial, fiscalização, incidente,
   solicitação em curso ou necessidade clínica documentada.
4. Obter aprovação da responsável técnica/controlador.
5. Eliminar banco, binário, índices derivados e cópias operacionais conforme expiração;
   registrar prova sem preservar o conteúdo eliminado.
6. Em backups imutáveis, impedir restauração para uso normal e deixar o dado expirar na
   janela documentada; se um backup antigo for restaurado, reaplicar a lista de
   eliminações antes de liberar o sistema.

O sistema ainda não implementa workflow de eliminação documental; a migration `0010`
nega `DELETE` ao role da aplicação. Até existir procedimento aprovado, a regra é
**preservar e escalar**, nunca apagar manualmente.

### 10.3. Solicitação de titular ou responsável

- Validar identidade e guarda legal fora de canal público.
- Registrar data, escopo e responsável pelo atendimento.
- Encaminhar à psicóloga/controlador; mantenedor não decide conteúdo clínico acessível.
- Exportar somente o necessário, por canal seguro, com protocolo de entrega.
- Não entregar materiais privativos de testes sem avaliação profissional.
- Registrar correções e restrições sem destruir trilha clínica/auditoria.
- Observar os prazos legais aplicáveis; a ANPD informa acesso imediato aos dados e até
  15 dias para declaração completa nas hipóteses legais.

---

## 11. Resposta a incidentes

### 11.1. O que conta como incidente

Evento confirmado que comprometa confidencialidade, integridade, disponibilidade ou
autenticidade: acesso indevido, documento trocado/corrompido, perda de SSD/HDD, backup
ilegível, ransomware, indisponibilidade prolongada, segredo exposto, envio ao destinatário
errado ou isolamento RLS quebrado. Vulnerabilidade não explorada é tratada com urgência,
mas só se torna incidente de dados quando há comprometimento confirmado.

Como há dados sensíveis, de menores e sob sigilo profissional, qualquer possível
exposição começa em **severidade alta** até avaliação documentada reduzir o nível.

### 11.2. Fluxo

1. **Detectar e declarar:** anotar quando o evento foi conhecido, quem detectou e sistemas
   potencialmente afetados.
2. **Conter:** bloquear conta/token, isolar host ou suspender frontend; não desligar/apagar
   indiscriminadamente se isso destruir evidência.
3. **Preservar:** coletar logs mínimos, estado de contêineres, commit, horário e hashes.
4. **Erradicar:** corrigir causa, reconstruir imagem/host limpo e rotacionar segredos.
5. **Avaliar titulares:** natureza/categoria dos dados, crianças afetadas, quantidade,
   possibilidade de identificação, cópia/exfiltração, duração e medidas existentes.
6. **Comunicar:** controlador/encarregado decide comunicação à ANPD e titulares.
7. **Recuperar:** usar conjunto coordenado anterior, validar e monitorar.
8. **Aprender:** relatório de causa raiz, controles, responsáveis e prazo; atualizar este
   manual e testes.

### 11.3. ANPD

Pela Resolução CD/ANPD nº 15/2024, incidente confirmado com dados pessoais que possa
acarretar risco ou dano relevante deve ser comunicado pelo controlador à ANPD e aos
titulares em até **três dias úteis** do conhecimento, ressalvado prazo legal específico.
Dados sensíveis, de crianças/adolescentes, de autenticação ou sob sigilo são critérios
expressos de risco relevante. Informação incompleta pode ser complementada, de forma
justificada, em até 20 dias úteis. O registro do incidente deve ser mantido por pelo
menos cinco anos.

O registro deve conter, no mínimo: natureza e data; categorias de dados/titulares;
medidas de proteção; riscos; causa, se conhecida; medidas de contenção/mitigação;
comunicações; critérios usados para comunicar ou não comunicar; responsáveis e lições.
Não guardar o próprio conteúdo clínico no relatório quando descrição categórica bastar.

Canal e formulário vigentes devem ser obtidos diretamente na página oficial da ANPD no
momento do evento; não confiar em cópia antiga do formulário.

### 11.4. Cenários rápidos

**Ransomware ou invasão:** isolar rede; não conectar o HDD/backup gravável ao host
suspeito; preservar evidência; rotacionar credenciais em dispositivo limpo; reconstruir
e restaurar. Não pagar nem apagar evidência por iniciativa técnica isolada.

**Documento ausente/hash inválido:** bloquear download; preservar banco e volume;
identificar último conjunto íntegro; não substituir apenas o arquivo sem reconciliar
metadados e auditoria.

**Disco quase cheio:** suspender uploads/tarefas pesadas; verificar WAL, logs, imagens e
volume; não apagar dados clínicos; expandir/migrar com backup.

**Segredo no Git/chat/log:** presumir comprometimento; revogar/rotacionar; invalidar
sessões quando aplicável; investigar uso; remover da visualização futura sem tratar
reescrita do histórico como substituta da rotação.

**RLS ou acesso cruzado:** suspender acesso imediatamente; preservar logs/auditoria;
identificar tenants e dados alcançáveis; tratar como incidente crítico de sigilo.

---

## 12. Checklist de abertura e fechamento de manutenção

### Antes

- [ ] Escopo e responsável definidos.
- [ ] Janela comunicada; ninguém registrando atendimento.
- [ ] `git status` limpo e commits anterior/novo anotados.
- [ ] Migration e novas variáveis revisadas.
- [ ] Testes unitários, integração aplicável, TypeScript e build aprovados.
- [ ] Backup banco + documentos do mesmo ponto, com hashes e snapshot Restic.
- [ ] Espaço, SMART, RAM e saúde dos serviços aceitáveis.
- [ ] Plano de retorno e critério de abortar definidos.

### Depois

- [ ] Contêineres `healthy`, sem OOM/restart inesperado.
- [ ] `/health` e `/health/ready` respondem.
- [ ] Migration em `head` esperado.
- [ ] Login e smoke funcional com dados sintéticos.
- [ ] RLS/role/auditoria verificados quando a mudança os alcança.
- [ ] Upload/download documental sintético verificado quando a mudança os alcança.
- [ ] Logs revistos sem PII.
- [ ] Registro operacional preenchido.
- [ ] Backup extraordinário pós-mudança feito se houve transformação relevante de dados.

---

## 13. Pendências obrigatórias antes do go-live

Este manual não transforma controles planejados em controles existentes. Permanecem:

- [ ] automatizar backup diário cifrado de banco + `documentos_data`;
- [ ] implementar WAL/base backup e monitoramento de `pg_stat_archiver`, ou registrar
  formalmente a decisão de operar apenas com RPO diário;
- [ ] implementar alerta de falha, espaço, SMART, OOM e ausência de snapshot;
- [ ] criar reconciliador somente-leitura banco↔volume para ausentes, órfãos, tamanho e hash;
- [ ] realizar primeiro restore coordenado e registrar RTO real;
- [ ] criar segunda cópia offline/off-site cifrada;
- [ ] inventariar e testar backup do banco, volume binário, workflows, credenciais e
  `N8N_ENCRYPTION_KEY` da instalação n8n antes de ativar a Fase 8;
- [ ] fixar dependências Python e imagens-base por lock/digest; até lá, preservar bundles
  das imagens Docker aprovadas a cada versão implantada;
- [ ] definir e aprovar política de retenção/eliminações e procedimento de *legal hold*;
- [ ] decidir Docker Secrets versus `.env` e executar rotação de credenciais expostas;
- [ ] concluir TLS/hardening de produção e então usar `COOKIE_SECURE=true`;
- [ ] implementar/reavaliar MFA da aplicação e controles administrativos;
- [ ] comprovar ZDR e ausência de opt-in de treino na organização/projeto OpenAI;
- [ ] formalizar contatos de incidente, controlador, privacidade e substituto;
- [ ] validar com responsável técnica/CRP o fluxo de materiais privativos de testes.

---

## 14. Referências primárias e técnicas

### Normas e orientação brasileiras

- [Lei nº 13.709/2018 — LGPD, texto compilado](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm) — dados sensíveis, crianças, segurança, incidentes, término e conservação.
- [ANPD — Comunicação de Incidente de Segurança](https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis) — critérios, prazo, comunicação em etapas e canal vigente.
- [ANPD — Resolução CD/ANPD nº 15/2024](https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-aprova-o-regulamento-de-comunicacao-de-incidente-de-seguranca) — regulamento de incidentes e retenção do registro.
- [ANPD — Guia de Segurança da Informação para agentes de pequeno porte](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/processo-guia-orientativo-sobre-seguranca-da-informacao-para-agentes-de-tratamento-de-pequeno-porte.pdf) — acesso, patches, backup, logs e treinamento.
- [Resolução CFP nº 1/2009, versão consolidada](https://atosoficiais.com.br/cfp/resolucao-do-exercicio-profissional-n-1-2009-dispoe-sobre-a-obrigatoriedade-do-registro-documental-decorrente-da-prestacao-de-servicos-psicologicos?origin=instituicao&q=registro+documental) — registro, sigilo, prontuário e guarda mínima.
- [Resolução CFP nº 6/2019](https://atosoficiais.com.br/cfp/resolucao-do-exercicio-profissional-n-6-2019-institui-regras-para-a-) — documentos psicológicos, condições de guarda e protocolo de entrega.
- [CFP — Resolução nº 31/2022 e SATEPSI](https://site.cfp.org.br/nova-resolucao-do-cfp-destaca-diretrizes-para-a-avaliacao-psicologica/) — avaliação e uso privativo de testes psicológicos.

### Backup, recuperação e incidentes

- [PostgreSQL 16 — Backup and Restore](https://www.postgresql.org/docs/16/backup.html).
- [PostgreSQL 16 — Continuous Archiving and PITR](https://www.postgresql.org/docs/16/continuous-archiving.html).
- [Docker — backup, restore e migração de volumes](https://docs.docker.com/engine/storage/volumes/).
- [Restic — documentação](https://restic.readthedocs.io/en/stable/), incluindo verificação, restauração, cifragem e retenção.
- [n8n — configuração de chave de criptografia](https://docs.n8n.io/hosting/configuration/configuration-examples/encryption-key/) — chave necessária para recuperar credenciais cifradas.
- [CISA StopRansomware Guide](https://www.cisa.gov/stopransomware/ransomware-guide) — cópias offline/cifradas e testes regulares.
- [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) — preparação, resposta e recuperação integradas ao risco.

---

*Revisar este documento após todo incidente, restore real, mudança arquitetural ou nova
regra aplicável. Procedimento não testado deve ser marcado como pendente; backup não
restaurado deve ser tratado como hipótese, não como garantia.*
