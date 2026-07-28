#!/usr/bin/env bash
# Exporta as imagens realmente implantadas, para recovery sem depender de tags mutaveis.
# Executar manualmente apos deploy validado; nao faz parte do backup rotineiro por I/O e espaco.
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly CONFIG_FILE="${AGENDA_BACKUP_CONFIG:-/etc/agenda-backup/agenda-backup.env}"

die() { printf 'ERRO: %s\n' "$*" >&2; exit 1; }

(( EUID == 0 )) || die "execute com sudo"

require_private_file() {
  local file="$1" mode owner
  [[ -f "$file" && -r "$file" ]] || die "arquivo obrigatorio inacessivel: $file"
  mode="$(stat -c '%a' -- "$file")"
  owner="$(stat -c '%U' -- "$file")"
  [[ "$owner" == root ]] || die "arquivo deve pertencer a root: $file"
  (( (8#$mode & 8#77) == 0 )) || die "permissoes inseguras em $file (esperado 0600)"
}

[[ -f "$CONFIG_FILE" ]] || die "configuracao ausente: $CONFIG_FILE"
require_private_file "$CONFIG_FILE"
# shellcheck disable=SC1090
source "$CONFIG_FILE"

readonly INFRA_DIR="${AGENDA_INFRA_DIR:-$(cd -- "$SCRIPT_DIR/.." && pwd -P)}"
readonly PROJECT_ROOT="$(cd -- "$INFRA_DIR/.." && pwd -P)"
readonly ENV_FILE="$PROJECT_ROOT/.env"
readonly COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$INFRA_DIR/docker-compose.yml")

: "${BACKUP_STAGE_ROOT:?BACKUP_STAGE_ROOT e obrigatorio}"
: "${BACKUP_STAGE_ENCRYPTION_ATTESTATION:?ateste de criptografia e obrigatorio}"
: "${RESTIC_REPOSITORY_FILE:?RESTIC_REPOSITORY_FILE e obrigatorio}"
: "${BACKUP_RESTIC_TIMEOUT_SECONDS:=1200}"
: "${BACKUP_IMAGE_TIMEOUT_SECONDS:=1800}"
: "${N8N_CONTAINER:=agenda-n8n-n8n-1}"
: "${N8N_POSTGRES_CONTAINER:=agenda-n8n-postgres-1}"

[[ "$BACKUP_STAGE_ROOT" = /* && "$BACKUP_STAGE_ROOT" != "/" ]] || die "staging invalido"
[[ "$BACKUP_STAGE_ENCRYPTION_ATTESTATION" == "confirmed" ]] || die "staging cifrado nao confirmado"
[[ -d "$BACKUP_STAGE_ROOT" ]] && mountpoint -q -- "$BACKUP_STAGE_ROOT" || die "staging cifrado nao montado"
require_private_file "$RESTIC_REPOSITORY_FILE"
[[ -r "$ENV_FILE" ]] || die ".env inacessivel"
[[ -f "$INFRA_DIR/docker-compose.yml" ]] || die "docker-compose.yml inexistente"
command -v docker >/dev/null || die "docker nao encontrado"
command -v restic >/dev/null || die "restic nao encontrado"
command -v sha256sum >/dev/null || die "sha256sum nao encontrado"
command -v timeout >/dev/null || die "timeout nao encontrado"
command -v flock >/dev/null || die "flock nao encontrado"
command -v git >/dev/null || die "git nao encontrado"
command -v sed >/dev/null || die "sed nao encontrado"
command -v tail >/dev/null || die "tail nao encontrado"
[[ "$BACKUP_RESTIC_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || die "timeout Restic invalido"
[[ "$BACKUP_IMAGE_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]] || die "timeout de imagens invalido"

[[ -t 0 ]] || die "backup manual exige terminal interativo para a senha Restic"
unset RESTIC_PASSWORD
read -r -s -p 'Senha do repositorio Restic: ' RESTIC_PASSWORD
printf '\n' >&2
[[ -n "$RESTIC_PASSWORD" ]] || die "senha Restic vazia"
export RESTIC_PASSWORD

timeout "${BACKUP_RESTIC_TIMEOUT_SECONDS}s" restic --repository-file "$RESTIC_REPOSITORY_FILE" snapshots >/dev/null
readonly LOCK_FILE="${BACKUP_LOCK_FILE:-/run/lock/agenda-backup.lock}"
mkdir -p -- "$(dirname -- "$LOCK_FILE")"
exec 9>"$LOCK_FILE"
flock -n 9 || die "ja existe backup em execucao"

readonly RUN_ID="imagens-$(date -u +%Y%m%dT%H%M%SZ)"
readonly BACKUP_RUN="$BACKUP_STAGE_ROOT/$RUN_ID"
trap 'status=$?; unset RESTIC_PASSWORD; if (( status != 0 )); then printf "Falha; estagio cifrado preservado: %s\\n" "$BACKUP_RUN" >&2; fi; exit "$status"' EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
mkdir --mode=0700 -- "$BACKUP_RUN"

[[ -z "$(git -C "$PROJECT_ROOT" status --porcelain --untracked-files=normal)" ]] || \
  die "arvore Git possui alteracoes locais ou arquivos nao rastreados"
readonly GIT_COMMIT="$(git -C "$PROJECT_ROOT" rev-parse HEAD)"

declare -a image_refs=()
declare -a services=()
declare -a containers=()
declare -a image_ids=()
for service in postgres backend frontend; do
  container="$("${COMPOSE[@]}" ps -q "$service")"
  [[ -n "$container" ]] || die "container $service nao encontrado"
  image_ref="$(docker inspect "$container" --format '{{.Config.Image}}')"
  [[ -n "$image_ref" ]] || die "imagem de $service nao encontrada"
  container_image_id="$(docker inspect "$container" --format '{{.Image}}')"
  tagged_image_id="$(docker image inspect "$image_ref" --format '{{.Id}}')"
  [[ -n "$container_image_id" && "$tagged_image_id" == "$container_image_id" ]] || \
    die "tag $image_ref nao corresponde a imagem executada por $service"
  revision="$(docker image inspect "$container_image_id" \
    --format '{{with index .Config.Labels "org.opencontainers.image.revision"}}{{.}}{{end}}')"
  if [[ "$service" == backend || "$service" == frontend ]]; then
    [[ "$revision" == "$GIT_COMMIT" ]] || \
      die "imagem de $service nao foi construida do commit $GIT_COMMIT (revisao: ${revision:-ausente})"
  fi
  services+=("$service")
  containers+=("$container")
  image_refs+=("$image_ref")
  image_ids+=("$container_image_id")
  printf '%s\t%s\t%s\t%s\n' "$service" "$image_ref" "$container_image_id" "${revision:--}" \
    >> "$BACKUP_RUN/imagens-em-execucao.txt"
done

# O n8n vive em outro projeto Compose/Portainer, mas integra o mesmo conjunto de
# recovery. Preservamos as imagens efetivamente executadas sem exigir labels Git.
for external_spec in "n8n:$N8N_CONTAINER" "n8n-postgres:$N8N_POSTGRES_CONTAINER"; do
  service="${external_spec%%:*}"
  container="${external_spec#*:}"
  docker inspect "$container" >/dev/null || die "container $service nao encontrado"
  image_ref="$(docker inspect "$container" --format '{{.Config.Image}}')"
  [[ -n "$image_ref" ]] || die "imagem de $service nao encontrada"
  container_image_id="$(docker inspect "$container" --format '{{.Image}}')"
  tagged_image_id="$(docker image inspect "$image_ref" --format '{{.Id}}')"
  [[ -n "$container_image_id" && "$tagged_image_id" == "$container_image_id" ]] || \
    die "tag $image_ref nao corresponde a imagem executada por $service"
  revision="$(docker image inspect "$container_image_id" \
    --format '{{with index .Config.Labels "org.opencontainers.image.revision"}}{{.}}{{end}}')"
  services+=("$service")
  containers+=("$container")
  image_refs+=("$image_ref")
  image_ids+=("$container_image_id")
  printf '%s\t%s\t%s\t%s\n' "$service" "$image_ref" "$container_image_id" "${revision:--}" \
    >> "$BACKUP_RUN/imagens-em-execucao.txt"
done

timeout "${BACKUP_IMAGE_TIMEOUT_SECONDS}s" docker image save "${image_refs[@]}" > "$BACKUP_RUN/imagens-docker.tar"
# Fecha a janela de corrida: nem a tag nem o container podem ter mudado enquanto
# o tar era criado. O bundle deve representar exatamente o runtime observado.
for i in "${!services[@]}"; do
  [[ "$(docker inspect "${containers[$i]}" --format '{{.Image}}')" == "${image_ids[$i]}" ]] || \
    die "container ${services[$i]} mudou durante o bundle"
  [[ "$(docker image inspect "${image_refs[$i]}" --format '{{.Id}}')" == "${image_ids[$i]}" ]] || \
    die "tag ${image_refs[$i]} mudou durante o bundle"
done
printf '%s\n' "$GIT_COMMIT" > "$BACKUP_RUN/git-commit.txt"
date -u +%Y-%m-%dT%H:%M:%SZ > "$BACKUP_RUN/criado-em-utc.txt"
(cd "$BACKUP_RUN" && sha256sum imagens-docker.tar git-commit.txt criado-em-utc.txt \
  imagens-em-execucao.txt > SHA256SUMS)
(cd "$BACKUP_RUN" && sha256sum --check SHA256SUMS >/dev/null)
[[ "$(git -C "$PROJECT_ROOT" rev-parse HEAD)" == "$GIT_COMMIT" ]] || \
  die "o commit mudou durante o bundle de imagens; conjunto recusado"

snapshot_output="$(timeout "${BACKUP_RESTIC_TIMEOUT_SECONDS}s" restic --repository-file "$RESTIC_REPOSITORY_FILE" \
  backup "$BACKUP_RUN" --tag agenda-imagens)"
snapshot_id="$(printf '%s\n' "$snapshot_output" | sed -n 's/.*snapshot \([[:xdigit:]]\{8,\}\).*/\1/p' | tail -n 1)"
[[ -n "$snapshot_id" ]] || die "Restic terminou sem informar o identificador do snapshot"
case "$BACKUP_RUN" in
  "$BACKUP_STAGE_ROOT"/*) rm -rf -- "$BACKUP_RUN" ;;
  *) die "recusa de limpar caminho fora do estagio" ;;
esac
printf 'Bundle de imagens concluido: snapshot %s\n' "$snapshot_id"
