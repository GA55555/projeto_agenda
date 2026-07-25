#!/usr/bin/env bash
# Configuracao unica do backup manual no servidor de producao.
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

die() { printf 'ERRO: %s\n' "$*" >&2; exit 1; }

(( EUID == 0 )) || die "execute com sudo"

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly INFRA_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
readonly CONFIG_DIR="/etc/agenda-backup"
readonly CONFIG_FILE="$CONFIG_DIR/agenda-backup.env"
readonly REPOSITORY_FILE="$CONFIG_DIR/restic-repository"
readonly STAGE_ROOT="${BACKUP_STAGE_ROOT:-/mnt/dados/agenda-backup-stage}"
readonly CIPHER_DIR="${BACKUP_CIPHER_DIR:-/mnt/dados/.agenda-stage-cipher}"
readonly RESTIC_REPOSITORY="${BACKUP_RESTIC_REPOSITORY:-/mnt/dados/agenda-restic}"

[[ -d "$CIPHER_DIR" && -f "$CIPHER_DIR/gocryptfs.conf" ]] || \
  die "cofre gocryptfs nao inicializado em $CIPHER_DIR"
[[ -d "$STAGE_ROOT" ]] || die "ponto de montagem ausente: $STAGE_ROOT"
[[ -d "$RESTIC_REPOSITORY" && -f "$RESTIC_REPOSITORY/config" ]] || \
  die "repositorio Restic nao inicializado em $RESTIC_REPOSITORY"
[[ -f "$INFRA_DIR/docker-compose.yml" && -f "$INFRA_DIR/../.env" ]] || \
  die "clone do projeto ou .env nao encontrado"

install -d -m 0700 -o root -g root "$CONFIG_DIR"
printf '%s\n' "$RESTIC_REPOSITORY" > "$REPOSITORY_FILE"
chmod 0600 "$REPOSITORY_FILE"

{
  printf 'BACKUP_STAGE_ROOT=%s\n' "$STAGE_ROOT"
  printf 'BACKUP_STAGE_ENCRYPTION_ATTESTATION=confirmed\n'
  printf 'BACKUP_CIPHER_DIR=%s\n' "$CIPHER_DIR"
  printf 'AGENDA_INFRA_DIR=%s\n' "$INFRA_DIR"
  printf 'RESTIC_REPOSITORY_FILE=%s\n' "$REPOSITORY_FILE"
  printf 'BACKUP_TAR_IMAGE=agenda-frontend:current\n'
  printf 'BACKUP_RESTIC_TIMEOUT_SECONDS=1200\n'
  printf 'BACKUP_HEALTH_TIMEOUT_SECONDS=120\n'
  printf 'BACKUP_IMAGE_TIMEOUT_SECONDS=1800\n'
  printf 'BACKUP_LOCK_FILE=/run/lock/agenda-backup.lock\n'
} > "$CONFIG_FILE"
chmod 0600 "$CONFIG_FILE"

printf 'Configuracao manual criada em %s (sem senhas).\n' "$CONFIG_FILE"
