#!/usr/bin/env bash
# Executa o baseline e registra o resultado no journald, sem payloads ou ambientes.
set -uo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly TAG="agenda-observabilidade"

output="$("$SCRIPT_DIR/verificar_runtime.sh" 2>&1)"
status=$?

if command -v logger >/dev/null 2>&1; then
  if (( status == 0 )); then
    logger --tag "$TAG" --priority user.notice -- "$output"
  else
    logger --tag "$TAG" --priority user.err -- "$output"
  fi
else
  printf '%s\n' "$output" >&2
  printf 'ERRO logger ausente; resultado nao foi registrado no journald\n' >&2
  exit 1
fi

printf '%s\n' "$output"
exit "$status"
