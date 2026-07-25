#!/usr/bin/env bash
# Backup coordenado da Agenda — Fase 8a.
#
# Este script deliberadamente NAO inicializa o Restic, nao cria diretorio em disco
# comum e nao agenda a si proprio. Ele so executa depois que o operador preparar
# um ponto de estagio CIFRADO e o cofre de credenciais fora do repositorio.
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly DEFAULT_CONFIG="/etc/agenda-backup/agenda-backup.env"
CONFIG_FILE="${AGENDA_BACKUP_CONFIG:-$DEFAULT_CONFIG}"

die() {
  printf 'ERRO: %s\n' "$*" >&2
  exit 1
}

(( EUID == 0 )) || die "execute com sudo"

require_private_file() {
  local file="$1"
  [[ -f "$file" && -r "$file" ]] || die "arquivo obrigatorio inacessivel: $file"
  local mode owner
  mode="$(stat -c '%a' -- "$file")"
  owner="$(stat -c '%U' -- "$file")"
  [[ "$owner" == root ]] || die "arquivo deve pertencer a root: $file"
  (( (8#$mode & 8#77) == 0 )) || die "permissoes inseguras em $file (esperado 0600)"
}

[[ -f "$CONFIG_FILE" ]] || die "configuracao ausente: $CONFIG_FILE"
require_private_file "$CONFIG_FILE"
# O arquivo fica fora do Git e e administrado pelo responsavel operacional.
# shellcheck disable=SC1090
source "$CONFIG_FILE"

readonly INFRA_DIR="${AGENDA_INFRA_DIR:-$(cd -- "$SCRIPT_DIR/.." && pwd -P)}"
readonly PROJECT_ROOT="$(cd -- "$INFRA_DIR/.." && pwd -P)"
readonly ENV_FILE="$PROJECT_ROOT/.env"
readonly COMPOSE=(docker compose --env-file "$ENV_FILE")

: "${BACKUP_STAGE_ROOT:?BACKUP_STAGE_ROOT e obrigatorio}"
: "${BACKUP_STAGE_ENCRYPTION_ATTESTATION:?ateste de criptografia e obrigatorio}"
: "${RESTIC_REPOSITORY_FILE:?RESTIC_REPOSITORY_FILE e obrigatorio}"
: "${BACKUP_TAR_IMAGE:=agenda-frontend:current}"
: "${BACKUP_RESTIC_TIMEOUT_SECONDS:=1200}"
: "${BACKUP_HEALTH_TIMEOUT_SECONDS:=120}"

[[ "$BACKUP_STAGE_ROOT" = /* && "$BACKUP_STAGE_ROOT" != "/" ]] || \
  die "BACKUP_STAGE_ROOT deve ser um caminho absoluto e nao pode ser /"
[[ "$BACKUP_STAGE_ENCRYPTION_ATTESTATION" == "confirmed" ]] || \
  die "o estagio cifrado nao foi confirmado explicitamente"
[[ -d "$BACKUP_STAGE_ROOT" ]] || die "diretorio de estagio inexistente: $BACKUP_STAGE_ROOT"
mountpoint -q -- "$BACKUP_STAGE_ROOT" || \
  die "o estagio deve ser um ponto de montagem dedicado e cifrado"

require_private_file "$RESTIC_REPOSITORY_FILE"
[[ -r "$ENV_FILE" ]] || die ".env inacessivel: $ENV_FILE"
[[ -f "$INFRA_DIR/docker-compose.yml" ]] || die "docker-compose.yml inexistente"
command -v docker >/dev/null || die "docker nao encontrado"
command -v restic >/dev/null || die "restic nao encontrado"
command -v sha256sum >/dev/null || die "sha256sum nao encontrado"
command -v timeout >/dev/null || die "timeout nao encontrado"
command -v flock >/dev/null || die "flock nao encontrado"
command -v tar >/dev/null || die "tar nao encontrado"
command -v git >/dev/null || die "git nao encontrado"
command -v mountpoint >/dev/null || die "mountpoint nao encontrado"
command -v sed >/dev/null || die "sed nao encontrado"
command -v sleep >/dev/null || die "sleep nao encontrado"
[[ "$BACKUP_RESTIC_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || die "timeout Restic invalido"
[[ "$BACKUP_HEALTH_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || die "timeout de healthcheck invalido"

[[ -t 0 ]] || die "backup manual exige terminal interativo para a senha Restic"
unset RESTIC_PASSWORD
read -r -s -p 'Senha do repositorio Restic: ' RESTIC_PASSWORD
printf '\n' >&2
[[ -n "$RESTIC_PASSWORD" ]] || die "senha Restic vazia"
export RESTIC_PASSWORD

# Nao parar o atendimento se o repositorio ou a imagem auxiliar ainda nao estiverem prontos.
timeout "${BACKUP_RESTIC_TIMEOUT_SECONDS}s" restic --repository-file "$RESTIC_REPOSITORY_FILE" \
  snapshots >/dev/null
docker image inspect "$BACKUP_TAR_IMAGE" >/dev/null

readonly LOCK_FILE="${BACKUP_LOCK_FILE:-/run/lock/agenda-backup.lock}"
mkdir -p -- "$(dirname -- "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
flock -n 9 || die "ja existe um backup coordenado em execucao"

readonly RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
readonly BACKUP_RUN="$BACKUP_STAGE_ROOT/$RUN_ID"
readonly REPORT_FILE="$BACKUP_RUN/relatorio.txt"
services_were_stopped=0

write_report() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$REPORT_FILE"
}

wait_for_healthy() {
  local service="$1" container health waited=0
  container="$("${COMPOSE[@]}" ps -q "$service")"
  [[ -n "$container" ]] || return 1
  while (( waited < BACKUP_HEALTH_TIMEOUT_SECONDS )); do
    health="$(docker inspect "$container" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}')"
    [[ "$health" == "healthy" ]] && return 0
    [[ "$health" == "exited" || "$health" == "dead" ]] && return 1
    sleep 2
    ((waited += 2))
  done
  return 1
}

restart_services() {
  if (( services_were_stopped )); then
    if ! "${COMPOSE[@]}" start backend frontend; then
      printf 'ERRO CRITICO: nao foi possivel reiniciar backend/frontend; intervenha imediatamente.\n' >&2
      return 1
    fi
    if ! wait_for_healthy backend || ! wait_for_healthy frontend; then
      printf 'ERRO CRITICO: backend/frontend nao ficaram saudaveis apos o backup.\n' >&2
      return 1
    fi
    services_were_stopped=0
  fi
}

on_exit() {
  local status=$?
  trap - EXIT
  if ! restart_services; then
    status=1
  fi
  if [[ -d "$BACKUP_RUN" ]]; then
    if (( status == 0 )); then
      write_report "resultado=sucesso"
    else
      write_report "resultado=falha codigo=$status; estagio preservado para analise"
    fi
  fi
  unset RESTIC_PASSWORD
  exit "$status"
}
trap on_exit EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

mkdir --mode=0700 -- "$BACKUP_RUN"
write_report "tipo=backup-coordenado run_id=$RUN_ID"
write_report "fase=8a sem-wal-pitr"

wait_for_healthy postgres || die "PostgreSQL nao esta saudavel antes do backup"
wait_for_healthy backend || die "backend nao esta saudavel antes do backup"
wait_for_healthy frontend || die "frontend nao esta saudavel antes do backup"

backend_container="$("${COMPOSE[@]}" ps -q backend)"
[[ -n "$backend_container" ]] || die "container backend nao encontrado"
docs_volume="$(docker inspect "$backend_container" --format '{{range .Mounts}}{{if eq .Destination "/app/data/documentos"}}{{.Name}}{{end}}{{end}}')"
[[ -n "$docs_volume" ]] || die "volume documental nao encontrado no backend"

# Um backup de recovery precisa reconstruir o codigo sem depender do GitHub. Alteracoes
# locais no servidor tornariam o commit, o binario e a configuracao ambiguos; por isso
# falhamos antes da pausa se a arvore versionada nao estiver limpa.
git -C "$PROJECT_ROOT" diff --quiet || die "arvore Git possui alteracoes locais nao commitadas"
git -C "$PROJECT_ROOT" diff --cached --quiet || die "indice Git possui alteracoes nao commitadas"
readonly GIT_COMMIT="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"
git -C "$PROJECT_ROOT" archive --format=tar --prefix=projeto_agenda/ "$GIT_COMMIT" > "$BACKUP_RUN/projeto_agenda-source.tar"
git -C "$PROJECT_ROOT" bundle create "$BACKUP_RUN/projeto_agenda.bundle" HEAD
git -C "$PROJECT_ROOT" bundle verify "$BACKUP_RUN/projeto_agenda.bundle" >/dev/null
write_report "fonte=git-archive-e-bundle"

# A pausa curta fecha a fronteira de escrita: Postgres continua ativo para o dump,
# mas nenhum request da aplicacao pode alterar banco ou documentos durante o conjunto.
services_were_stopped=1
"${COMPOSE[@]}" stop frontend backend

timeout 20m "${COMPOSE[@]}" exec -T postgres sh -lc \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$BACKUP_RUN/agenda.dump"
timeout 5m "${COMPOSE[@]}" exec -T postgres sh -lc \
  'pg_dumpall -U "$POSTGRES_USER" --globals-only' > "$BACKUP_RUN/globals.sql"

# O volume e lido por um container sem rede e somente-leitura. O arquivo gerado
# existe apenas no estagio cifrado e sera enviado ao Restic tambem cifrado.
timeout 15m docker run --rm --network none --read-only --entrypoint tar \
  -v "$docs_volume:/source:ro" -v "$BACKUP_RUN:/backup:rw" \
  "$BACKUP_TAR_IMAGE" -C /source -cf /backup/documentos.tar .

printf '%s\n' "$GIT_COMMIT" > "$BACKUP_RUN/git-commit.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$BACKUP_RUN/criado-em-utc.txt"
"${COMPOSE[@]}" exec -T postgres postgres --version > "$BACKUP_RUN/postgres-version.txt"
"${COMPOSE[@]}" run --rm --no-deps backend alembic current > "$BACKUP_RUN/alembic-current.txt"
install -d -m 0700 "$BACKUP_RUN/config"
install -m 0600 "$ENV_FILE" "$BACKUP_RUN/config/.env"
install -m 0600 "$INFRA_DIR/docker-compose.yml" "$BACKUP_RUN/config/docker-compose.yml"
install -m 0600 "$INFRA_DIR/postgres/postgresql.conf" "$BACKUP_RUN/config/postgresql.conf"

(cd "$BACKUP_RUN" && sha256sum \
  agenda.dump globals.sql documentos.tar projeto_agenda-source.tar projeto_agenda.bundle \
  git-commit.txt criado-em-utc.txt postgres-version.txt alembic-current.txt \
  config/.env config/docker-compose.yml config/postgresql.conf > SHA256SUMS)

# A indisponibilidade termina antes das verificacoes e do envio ao Restic.
restart_services

"${COMPOSE[@]}" exec -T postgres pg_restore --list < "$BACKUP_RUN/agenda.dump" >/dev/null
tar -tf "$BACKUP_RUN/documentos.tar" >/dev/null
tar -tf "$BACKUP_RUN/projeto_agenda-source.tar" >/dev/null
git -C "$PROJECT_ROOT" bundle verify "$BACKUP_RUN/projeto_agenda.bundle" >/dev/null
(cd "$BACKUP_RUN" && sha256sum --check SHA256SUMS >/dev/null)
[[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" == "$GIT_COMMIT" ]] || \
  die "o commit mudou durante o backup; conjunto recusado"
write_report "artefatos=validados"

snapshot_output="$(timeout "${BACKUP_RESTIC_TIMEOUT_SECONDS}s" restic --repository-file "$RESTIC_REPOSITORY_FILE" \
  backup "$BACKUP_RUN" --tag agenda-coordenado)"
snapshot_id="$(printf '%s\n' "$snapshot_output" | sed -n 's/.*snapshot \([[:xdigit:]]\{8,\}\).*/\1/p' | tail -n 1)"
[[ -n "$snapshot_id" ]] || die "Restic terminou sem informar o identificador do snapshot"

# Remove somente o diretorio de execucao criado por este processo, sempre dentro do
# ponto de montagem validado. Nao executa retention nem prune: isso requer credencial
# administrativa e revisao humana separada.
case "$BACKUP_RUN" in
  "$BACKUP_STAGE_ROOT"/*) rm -rf -- "$BACKUP_RUN" ;;
  *) die "recusa de limpar caminho fora do estagio" ;;
esac
printf 'Backup coordenado concluido: snapshot %s\n' "$snapshot_id"
