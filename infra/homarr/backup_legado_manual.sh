#!/usr/bin/env bash
# Backup consistente do Homarr 0.x para a migração paralela.
# Monta o staging cifrado, recebe o ZIP oficial, captura stack/imagem/volumes,
# reinicia o legado e envia o conjunto validado ao Restic.
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

die() {
  printf 'ERRO: %s\n' "$*" >&2
  exit 1
}

(( EUID == 0 )) || die "execute com sudo"
[[ -t 0 ]] || die "a execução exige terminal interativo"

readonly CONFIG_FILE="${AGENDA_BACKUP_CONFIG:-/etc/agenda-backup/agenda-backup.env}"
readonly HOMARR_CONTAINER="${HOMARR_CONTAINER:-homarr}"
readonly PORTAINER_CONTAINER="${PORTAINER_CONTAINER:-portainer}"
readonly TAR_IMAGE="${HOMARR_BACKUP_TAR_IMAGE:-agenda-frontend:current}"
readonly HEALTH_TIMEOUT="${HOMARR_HEALTH_TIMEOUT_SECONDS:-120}"
readonly RESTIC_TIMEOUT="${HOMARR_RESTIC_TIMEOUT_SECONDS:-1800}"

require_private_file() {
  local file="$1" mode owner
  [[ -f "$file" && -r "$file" ]] || die "arquivo obrigatório inacessível: $file"
  mode="$(stat -c '%a' -- "$file")"
  owner="$(stat -c '%U' -- "$file")"
  [[ "$owner" == root ]] || die "arquivo deve pertencer a root: $file"
  (( (8#$mode & 8#77) == 0 )) || die "permissões inseguras em $file"
}

require_private_file "$CONFIG_FILE"
# Configuração operacional root-only, nunca impressa ou copiada para o conjunto.
# shellcheck disable=SC1090
source "$CONFIG_FILE"

: "${BACKUP_STAGE_ROOT:?BACKUP_STAGE_ROOT é obrigatório}"
: "${BACKUP_CIPHER_DIR:?BACKUP_CIPHER_DIR é obrigatório}"
: "${RESTIC_REPOSITORY_FILE:?RESTIC_REPOSITORY_FILE é obrigatório}"

[[ "$BACKUP_STAGE_ROOT" = /* && "$BACKUP_STAGE_ROOT" != / ]] || \
  die "staging deve ser caminho absoluto e diferente de /"
[[ -d "$BACKUP_STAGE_ROOT" ]] || die "ponto de montagem do staging não existe"
[[ -d "$BACKUP_CIPHER_DIR" && -f "$BACKUP_CIPHER_DIR/gocryptfs.conf" ]] || \
  die "cofre gocryptfs inválido"
require_private_file "$RESTIC_REPOSITORY_FILE"

for command_name in chmod chown cut date docker find findmnt flock gocryptfs id install \
  mkdir mountpoint restic sed sha256sum sleep sort stat tail tar timeout umount unzip xargs; do
  command -v "$command_name" >/dev/null || die "comando ausente: $command_name"
done
[[ "$HEALTH_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || die "timeout de saúde inválido"
[[ "$RESTIC_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || die "timeout Restic inválido"

readonly OPERATOR="${SUDO_USER:-root}"
readonly RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_RUN="$BACKUP_STAGE_ROOT/homarr-migracao-$RUN_ID"
readonly LOCK_FILE="/run/lock/agenda-homarr-migracao.lock"

(( $# == 1 )) || die "uso: sudo $0 /caminho/privado/export-homarr.zip"
ZIP_SOURCE="$1"
[[ "$ZIP_SOURCE" = /* ]] || die "informe o ZIP por caminho absoluto"
[[ "$ZIP_SOURCE" == *.zip || "$ZIP_SOURCE" == *.ZIP ]] || die "arquivo deve terminar em .zip"
zip_source_available=0
if [[ -e "$ZIP_SOURCE" || -L "$ZIP_SOURCE" ]]; then
  [[ -f "$ZIP_SOURCE" && ! -L "$ZIP_SOURCE" ]] || die "ZIP deve ser arquivo regular"
  zip_owner="$(stat -c '%U' -- "$ZIP_SOURCE")"
  zip_mode="$(stat -c '%a' -- "$ZIP_SOURCE")"
  [[ "$zip_owner" == "$OPERATOR" ]] || die "ZIP deve pertencer ao usuário operador"
  (( (8#$zip_mode & 8#77) == 0 )) || \
    die "ZIP deve estar restrito ao proprietário (modo 0600)"
  unzip -tq "$ZIP_SOURCE" >/dev/null || die "ZIP de migração inválido"
  zip_source_available=1
fi

mkdir -p -- "$(dirname -- "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
flock -n 9 || die "já existe uma migração Homarr em execução"

stage_mounted=0
homarr_stopped=0

wait_for_homarr() {
  local waited=0 state health
  while (( waited < HEALTH_TIMEOUT )); do
    state="$(docker inspect "$HOMARR_CONTAINER" --format '{{.State.Status}}' 2>/dev/null || true)"
    health="$(docker inspect "$HOMARR_CONTAINER" \
      --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
      2>/dev/null || true)"
    [[ "$state" == running && "$health" == healthy ]] && return 0
    [[ "$state" == dead ]] && return 1
    sleep 2
    ((waited += 2))
  done
  return 1
}

restart_homarr() {
  if (( homarr_stopped )); then
    docker start "$HOMARR_CONTAINER" >/dev/null || return 1
    homarr_stopped=0
    wait_for_homarr
  fi
}

on_exit() {
  local status=$?
  trap - EXIT
  if ! restart_homarr; then
    printf 'ERRO CRÍTICO: Homarr não retornou saudável; verifique-o imediatamente.\n' >&2
    status=1
  fi
  unset RESTIC_PASSWORD
  if (( stage_mounted )) && mountpoint -q -- "$BACKUP_STAGE_ROOT"; then
    if ! umount -- "$BACKUP_STAGE_ROOT"; then
      printf 'ERRO CRÍTICO: staging cifrado permaneceu montado.\n' >&2
      status=1
    fi
  fi
  exit "$status"
}
trap on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if ! mountpoint -q -- "$BACKUP_STAGE_ROOT"; then
  printf 'Digite a senha do gocryptfs; ela não será armazenada.\n' >&2
  gocryptfs "$BACKUP_CIPHER_DIR" "$BACKUP_STAGE_ROOT"
fi
stage_mounted=1

fstype="$(findmnt -n -o FSTYPE --target "$BACKUP_STAGE_ROOT")"
mount_source="$(findmnt -n -o SOURCE --target "$BACKUP_STAGE_ROOT")"
[[ "$fstype" == fuse.gocryptfs ]] || die "staging não usa gocryptfs"
[[ "$mount_source" == "$BACKUP_CIPHER_DIR" ]] || die "origem inesperada do staging"

mapfile -d '' prior_runs < <(find "$BACKUP_STAGE_ROOT" -mindepth 1 -maxdepth 1 \
  -type d -name 'homarr-migracao-*' -print0)
if (( zip_source_available )); then
  (( ${#prior_runs[@]} == 0 )) || \
    die "há execução cifrada incompleta; não consumir um novo ZIP"
  mkdir --mode=0700 -- "$BACKUP_RUN"
  zip_hash_before="$(sha256sum "$ZIP_SOURCE" | cut -d ' ' -f 1)"
  install -m 0600 "$ZIP_SOURCE" "$BACKUP_RUN/homarr-export.zip"
  zip_hash_after="$(sha256sum "$BACKUP_RUN/homarr-export.zip" | cut -d ' ' -f 1)"
  [[ "$zip_hash_before" == "$zip_hash_after" ]] || die "cópia do ZIP divergiu"
  rm -f -- "$ZIP_SOURCE"
else
  (( ${#prior_runs[@]} == 1 )) || \
    die "ZIP privado ausente e não há uma única execução cifrada para retomar"
  BACKUP_RUN="${prior_runs[0]}"
  case "$BACKUP_RUN" in
    "$BACKUP_STAGE_ROOT"/homarr-migracao-*) ;;
    *) die "execução anterior possui caminho inesperado" ;;
  esac
  printf 'Retomando a execução cifrada incompleta anterior.\n'
fi
[[ -f "$BACKUP_RUN/homarr-export.zip" ]] || die "ZIP cifrado ausente"
unzip -tq "$BACKUP_RUN/homarr-export.zip" >/dev/null || die "ZIP cifrado inválido"

docker inspect "$HOMARR_CONTAINER" >/dev/null || die "container Homarr ausente"
[[ "$(docker inspect "$HOMARR_CONTAINER" --format '{{.State.Status}}')" == running ]] || \
  die "Homarr não está em execução"
[[ "$(docker inspect "$HOMARR_CONTAINER" \
  --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}')" == healthy ]] || \
  die "Homarr não está saudável"
[[ "$(docker inspect "$HOMARR_CONTAINER" --format '{{.RestartCount}}')" == 0 ]] || \
  die "Homarr possui reinícios; diagnostique antes do backup"

configs_volume="$(docker inspect "$HOMARR_CONTAINER" --format \
  '{{range .Mounts}}{{if eq .Destination "/app/data/configs"}}{{.Name}}{{end}}{{end}}')"
icons_volume="$(docker inspect "$HOMARR_CONTAINER" --format \
  '{{range .Mounts}}{{if eq .Destination "/app/public/icons"}}{{.Name}}{{end}}{{end}}')"
data_volume="$(docker inspect "$HOMARR_CONTAINER" --format \
  '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}')"
for volume_name in "$configs_volume" "$icons_volume" "$data_volume"; do
  [[ "$volume_name" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || die "volume Homarr inválido"
  docker volume inspect "$volume_name" >/dev/null || die "volume Homarr ausente"
done
[[ "$configs_volume" != "$icons_volume" && "$configs_volume" != "$data_volume" && \
   "$icons_volume" != "$data_volume" ]] || die "os três volumes devem ser distintos"

socket_mount="$(docker inspect "$HOMARR_CONTAINER" --format \
  '{{range .Mounts}}{{if eq .Destination "/var/run/docker.sock"}}{{.Type}}:{{.RW}}{{end}}{{end}}')"
[[ "$socket_mount" == bind:true ]] || die "topologia do socket Docker divergiu"

docker image inspect "$TAR_IMAGE" >/dev/null || die "imagem auxiliar local ausente"
legacy_image_id="$(docker inspect "$HOMARR_CONTAINER" --format '{{.Image}}')"
docker image inspect "$legacy_image_id" >/dev/null || die "imagem legada ausente"

compose_file="$(docker inspect "$HOMARR_CONTAINER" --format \
  '{{index .Config.Labels "com.docker.compose.project.config_files"}}')"
[[ "$compose_file" =~ ^/data/compose/[0-9]+/docker-compose\.ya?ml$ ]] || \
  die "caminho da stack Portainer inesperado"

install -d -m 0700 "$BACKUP_RUN/stack"
docker cp "$PORTAINER_CONTAINER:$compose_file" "$BACKUP_RUN/stack/docker-compose.yml" || \
  die "definição da stack não encontrada no Portainer"
[[ -s "$BACKUP_RUN/stack/docker-compose.yml" ]] || die "definição da stack está vazia"
chmod 0600 "$BACKUP_RUN/stack/docker-compose.yml"
docker inspect "$HOMARR_CONTAINER" > "$BACKUP_RUN/stack/container-inspect.json"
chmod 0600 "$BACKUP_RUN/stack/container-inspect.json"
docker image inspect "$legacy_image_id" > "$BACKUP_RUN/stack/image-inspect.json"
chmod 0600 "$BACKUP_RUN/stack/image-inspect.json"

printf 'Preservando a imagem legada antes da pausa...\n'
timeout --foreground --kill-after=10s 15m \
  docker save --output "$BACKUP_RUN/homarr-legado-image.tar" "$legacy_image_id"

printf 'Parando somente o Homarr para capturar os três volumes...\n'
homarr_stopped=1
docker stop --time 30 "$HOMARR_CONTAINER" >/dev/null

archive_volume() {
  local volume="$1" output="$2"
  timeout --foreground --kill-after=10s 10m \
    docker run --rm --network none --read-only --entrypoint tar \
      -v "$volume:/source:ro" -v "$BACKUP_RUN:/backup:rw" \
      "$TAR_IMAGE" -C /source -cf "/backup/$output" .
}

archive_volume "$configs_volume" homarr-configs.tar
archive_volume "$icons_volume" homarr-icons.tar
archive_volume "$data_volume" homarr-data.tar

printf 'Reiniciando o Homarr legado...\n'
restart_homarr || die "Homarr não retornou saudável"

tar -tf "$BACKUP_RUN/homarr-configs.tar" >/dev/null
tar -tf "$BACKUP_RUN/homarr-icons.tar" >/dev/null
tar -tf "$BACKUP_RUN/homarr-data.tar" >/dev/null
tar -tf "$BACKUP_RUN/homarr-legado-image.tar" >/dev/null
unzip -tq "$BACKUP_RUN/homarr-export.zip" >/dev/null

printf '%s\n' "$legacy_image_id" > "$BACKUP_RUN/legacy-image-id.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$BACKUP_RUN/criado-em-utc.txt"
(cd "$BACKUP_RUN" && \
  find . -type f ! -name SHA256SUMS -print0 | sort -z | \
  xargs -0 sha256sum > SHA256SUMS)
(cd "$BACKUP_RUN" && sha256sum --check SHA256SUMS >/dev/null)

printf 'Digite a senha do Restic; ela não será armazenada.\n' >&2
read -r -s RESTIC_PASSWORD
printf '\n' >&2
[[ -n "$RESTIC_PASSWORD" ]] || die "senha Restic vazia"
export RESTIC_PASSWORD
timeout "${RESTIC_TIMEOUT}s" restic --repository-file "$RESTIC_REPOSITORY_FILE" \
  snapshots >/dev/null
snapshot_output="$(timeout "${RESTIC_TIMEOUT}s" restic \
  --repository-file "$RESTIC_REPOSITORY_FILE" backup "$BACKUP_RUN" \
  --tag homarr-migracao)"
snapshot_id="$(printf '%s\n' "$snapshot_output" | \
  sed -n 's/.*snapshot \([[:xdigit:]]\{8,\}\).*/\1/p' | tail -n 1)"
[[ -n "$snapshot_id" ]] || die "Restic não informou o snapshot"
timeout "${RESTIC_TIMEOUT}s" restic --repository-file "$RESTIC_REPOSITORY_FILE" check

case "$BACKUP_RUN" in
  "$BACKUP_STAGE_ROOT"/homarr-migracao-*) rm -rf -- "$BACKUP_RUN" ;;
  *) die "recusa de limpar caminho inesperado" ;;
esac
printf 'Backup Homarr concluído e verificado: snapshot %s\n' "$snapshot_id"
