#!/usr/bin/env bash
# Baseline manual de observabilidade da Agenda e do pipeline n8n.
set -uo pipefail
IFS=$'\n\t'

readonly MEMORY_WARN_PERCENT="${AGENDA_MEMORY_WARN_PERCENT:-80}"
readonly DISK_WARN_PERCENT="${AGENDA_DISK_WARN_PERCENT:-85}"
readonly -a REQUIRED_CONTAINERS=(
  agenda_postgres
  agenda_backend
  agenda_frontend
  agenda-n8n-postgres-1
  agenda-n8n-n8n-1
  agenda-n8n-task-runners-1
)

errors=0
warnings=0

error() {
  printf 'ERRO %s\n' "$*" >&2
  ((errors += 1))
}

warn() {
  printf 'AVISO %s\n' "$*" >&2
  ((warnings += 1))
}

is_percent() {
  [[ "$1" =~ ^([0-9]|[1-9][0-9]|100)$ ]]
}

is_percent "$MEMORY_WARN_PERCENT" || {
  printf 'ERRO limiar de memória inválido: %s\n' "$MEMORY_WARN_PERCENT" >&2
  exit 1
}
is_percent "$DISK_WARN_PERCENT" || {
  printf 'ERRO limiar de disco inválido: %s\n' "$DISK_WARN_PERCENT" >&2
  exit 1
}
command -v docker >/dev/null || { printf 'ERRO docker ausente\n' >&2; exit 1; }
command -v df >/dev/null || { printf 'ERRO df ausente\n' >&2; exit 1; }
command -v awk >/dev/null || { printf 'ERRO awk ausente\n' >&2; exit 1; }

for container in "${REQUIRED_CONTAINERS[@]}"; do
  if ! docker inspect "$container" >/dev/null 2>&1; then
    error "container=$container ausente"
    continue
  fi

  state="$(docker inspect "$container" --format '{{.State.Status}}')"
  health="$(docker inspect "$container" \
    --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}')"
  restarts="$(docker inspect "$container" --format '{{.RestartCount}}')"
  oom="$(docker inspect "$container" --format '{{.State.OOMKilled}}')"
  memory_limit="$(docker inspect "$container" --format '{{.HostConfig.Memory}}')"
  memory_raw="$(docker stats "$container" --no-stream --format '{{.MemPerc}}' 2>/dev/null)"
  memory_percent="${memory_raw%\%}"

  [[ "$state" == running ]] || error "container=$container estado=$state"
  [[ "$health" == none || "$health" == healthy ]] || \
    error "container=$container health=$health"
  [[ "$restarts" == 0 ]] || error "container=$container reinícios=$restarts"
  [[ "$oom" == false ]] || error "container=$container oom=true"
  [[ "$memory_limit" =~ ^[1-9][0-9]*$ ]] || error "container=$container sem-limite-memória"
  if [[ "$memory_percent" =~ ^[0-9]+([.][0-9]+)?$ ]] && \
     awk -v current="$memory_percent" -v limit="$MEMORY_WARN_PERCENT" \
       'BEGIN { exit !(current >= limit) }'; then
    warn "container=$container memória=${memory_percent}% limite=${MEMORY_WARN_PERCENT}%"
  fi

  printf 'OK container=%s estado=%s health=%s reinícios=%s oom=%s memória=%s%%\n' \
    "$container" "$state" "$health" "$restarts" "$oom" "${memory_percent:-indisponível}"
done

disk_percent="$(df -P /var/lib/docker 2>/dev/null | awk 'NR==2 {gsub(/%/, "", $5); print $5}')"
if [[ ! "$disk_percent" =~ ^[0-9]+$ ]]; then
  error "uso de disco indisponível"
elif (( disk_percent >= DISK_WARN_PERCENT )); then
  warn "disco=${disk_percent}% limite=${DISK_WARN_PERCENT}%"
else
  printf 'OK disco=%s%% limite=%s%%\n' "$disk_percent" "$DISK_WARN_PERCENT"
fi

unbounded_logs=0
for container in "${REQUIRED_CONTAINERS[@]}"; do
  docker inspect "$container" >/dev/null 2>&1 || continue
  log_driver="$(docker inspect "$container" --format '{{.HostConfig.LogConfig.Type}}')"
  log_max_size="$(docker inspect "$container" \
    --format '{{index .HostConfig.LogConfig.Config "max-size"}}')"
  log_max_file="$(docker inspect "$container" \
    --format '{{index .HostConfig.LogConfig.Config "max-file"}}')"
  if [[ "$log_driver" == json-file && ( -z "$log_max_size" || -z "$log_max_file" ) ]]; then
    ((unbounded_logs += 1))
  fi
done
if (( unbounded_logs )); then
  warn "logs=json-file-sem-rotação containers=$unbounded_logs"
else
  printf 'OK política-de-logs=limitada\n'
fi

printf 'RESUMO erros=%s avisos=%s\n' "$errors" "$warnings"
(( errors == 0 )) || exit 1
(( warnings == 0 )) || exit 2
exit 0
