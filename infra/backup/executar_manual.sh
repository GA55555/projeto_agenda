#!/usr/bin/env bash
# Uma unica entrada para a janela manual: monta, executa e desmonta o staging cifrado.
set -Eeuo pipefail
IFS=$'\n\t'
umask 077

die() { printf 'ERRO: %s\n' "$*" >&2; exit 1; }

(( EUID == 0 )) || die "execute com sudo"

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly CONFIG_FILE="${AGENDA_BACKUP_CONFIG:-/etc/agenda-backup/agenda-backup.env}"
[[ -f "$CONFIG_FILE" && -r "$CONFIG_FILE" ]] || die "execute configurar_manual.sh primeiro"
config_mode="$(stat -c '%a' -- "$CONFIG_FILE")"
config_owner="$(stat -c '%U' -- "$CONFIG_FILE")"
[[ "$config_owner" == root ]] || die "configuracao deve pertencer a root"
(( (8#$config_mode & 8#77) == 0 )) || die "configuracao deve ter permissao 0600"
# shellcheck disable=SC1090
source "$CONFIG_FILE"

: "${BACKUP_STAGE_ROOT:?BACKUP_STAGE_ROOT e obrigatorio}"
: "${BACKUP_CIPHER_DIR:?BACKUP_CIPHER_DIR e obrigatorio}"
[[ -d "$BACKUP_CIPHER_DIR" && -f "$BACKUP_CIPHER_DIR/gocryptfs.conf" ]] || \
  die "cofre gocryptfs invalido"
[[ -d "$BACKUP_STAGE_ROOT" ]] || die "ponto de montagem ausente"
command -v gocryptfs >/dev/null || die "gocryptfs nao encontrado"
command -v mountpoint >/dev/null || die "mountpoint nao encontrado"
command -v findmnt >/dev/null || die "findmnt nao encontrado"
command -v umount >/dev/null || die "umount nao encontrado"
unmount_on_exit=0

unmount_stage() {
  local status=$?
  trap - EXIT
  if (( unmount_on_exit )) && mountpoint -q -- "$BACKUP_STAGE_ROOT"; then
    if ! umount -- "$BACKUP_STAGE_ROOT"; then
      printf 'ERRO CRITICO: staging permaneceu montado em %s\n' "$BACKUP_STAGE_ROOT" >&2
      status=1
    fi
  fi
  exit "$status"
}
trap unmount_stage EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

if ! mountpoint -q -- "$BACKUP_STAGE_ROOT"; then
  printf 'Digite a senha do gocryptfs. Ela nao sera armazenada.\n' >&2
  gocryptfs "$BACKUP_CIPHER_DIR" "$BACKUP_STAGE_ROOT"
  unmount_on_exit=1
fi

fstype="$(findmnt -n -o FSTYPE --target "$BACKUP_STAGE_ROOT")"
[[ "$fstype" == fuse.gocryptfs ]] || die "staging montado com tipo inesperado: $fstype"
mount_source="$(findmnt -n -o SOURCE --target "$BACKUP_STAGE_ROOT")"
[[ "$mount_source" == "$BACKUP_CIPHER_DIR" ]] || \
  die "staging montado a partir de origem inesperada: $mount_source"
unmount_on_exit=1

case "${1:-backup}" in
  backup) target_script="$SCRIPT_DIR/backup_coordenado.sh" ;;
  imagens) target_script="$SCRIPT_DIR/backup_imagens_aprovadas.sh" ;;
  *) die "uso: executar_manual.sh [backup|imagens]" ;;
esac

AGENDA_BACKUP_CONFIG="$CONFIG_FILE" /bin/bash "$target_script"
printf 'Operacao concluida; desmontando staging cifrado.\n'
