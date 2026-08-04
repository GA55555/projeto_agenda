#!/usr/bin/env bash
set -Eeuo pipefail

readonly INPUT_CHAIN="AGENDA-LAN-INPUT"
readonly DOCKER_CHAIN="AGENDA-LAN-DOCKER"
readonly LEGACY_CHAIN="AGENDA-LAN-GUARD"
readonly LAN_INTERFACE="${AGENDA_LAN_INTERFACE:-enp2s0}"
readonly -a PROTECTED_PORTS=(5432 8000 8080 8081 8443 9443)
readonly -a FIREWALL_BINARIES=(/usr/sbin/iptables /usr/sbin/ip6tables)

require_root() {
  if [[ ${EUID} -ne 0 ]]; then
    echo "ERRO: execute como root." >&2
    exit 1
  fi
}

chain_exists() {
  local firewall=$1
  local chain=$2
  "$firewall" -S "$chain" >/dev/null 2>&1
}

delete_jump() {
  local firewall=$1
  local parent_chain=$2
  local target_chain=$3

  while chain_exists "$firewall" "$parent_chain" \
    && "$firewall" -C "$parent_chain" -j "$target_chain" >/dev/null 2>&1; do
    "$firewall" -D "$parent_chain" -j "$target_chain"
  done
}

delete_chain() {
  local firewall=$1
  local chain=$2

  if chain_exists "$firewall" "$chain"; then
    "$firewall" -F "$chain"
    "$firewall" -X "$chain"
  fi
}

preflight() {
  local firewall

  if [[ ! $LAN_INTERFACE =~ ^[[:alnum:]_.:-]+$ ]]; then
    echo "ERRO: nome de interface invalido." >&2
    exit 1
  fi

  /usr/sbin/ip link show dev "$LAN_INTERFACE" >/dev/null

  for firewall in "${FIREWALL_BINARIES[@]}"; do
    if [[ ! -x $firewall ]]; then
      echo "ERRO: binario ausente: $firewall" >&2
      exit 1
    fi
    if ! chain_exists "$firewall" INPUT; then
      echo "ERRO: chain INPUT indisponivel em $firewall." >&2
      exit 1
    fi
    if ! chain_exists "$firewall" DOCKER-USER; then
      echo "ERRO: chain DOCKER-USER indisponivel em $firewall; o Docker deve estar ativo." >&2
      exit 1
    fi
  done
}

validate_family_syntax() {
  local firewall=$1
  local restore_binary="${firewall}-restore"

  if [[ ! -x $restore_binary ]]; then
    echo "ERRO: binario ausente: $restore_binary" >&2
    exit 1
  fi

  printf '%s\n' \
    '*filter' \
    ':AGENDA-SYNTAX-IN - [0:0]' \
    ':AGENDA-SYNTAX-DKR - [0:0]' \
    "-A AGENDA-SYNTAX-IN -i $LAN_INTERFACE -p tcp --dport 8080 -j DROP" \
    "-A AGENDA-SYNTAX-DKR -i $LAN_INTERFACE -p tcp -m conntrack --ctorigdstport 8080 -j DROP" \
    'COMMIT' \
    | "$restore_binary" --test --noflush
}

check_rules() {
  local firewall

  preflight
  for firewall in "${FIREWALL_BINARIES[@]}"; do
    validate_family_syntax "$firewall"
  done
  echo "Pre-validacao do firewall aprovada para IPv4 e IPv6."
}

apply_family() {
  local firewall=$1
  local port

  if ! chain_exists "$firewall" "$INPUT_CHAIN"; then
    "$firewall" -N "$INPUT_CHAIN"
  fi
  if ! chain_exists "$firewall" "$DOCKER_CHAIN"; then
    "$firewall" -N "$DOCKER_CHAIN"
  fi
  "$firewall" -F "$INPUT_CHAIN"
  "$firewall" -F "$DOCKER_CHAIN"

  for port in "${PROTECTED_PORTS[@]}"; do
    "$firewall" -A "$INPUT_CHAIN" \
      -i "$LAN_INTERFACE" \
      -p tcp --dport "$port" \
      -m comment --comment "agenda: bloquear porta local na LAN" \
      -j DROP
    "$firewall" -A "$DOCKER_CHAIN" \
      -i "$LAN_INTERFACE" \
      -p tcp \
      -m conntrack --ctorigdstport "$port" \
      -m comment --comment "agenda: bloquear porta publicada na LAN" \
      -j DROP
  done
  "$firewall" -A "$INPUT_CHAIN" -j RETURN
  "$firewall" -A "$DOCKER_CHAIN" -j RETURN

  # Reinsere no topo para ficar antes dos saltos do UFW e do RETURN do Docker.
  delete_jump "$firewall" INPUT "$INPUT_CHAIN"
  delete_jump "$firewall" DOCKER-USER "$DOCKER_CHAIN"
  "$firewall" -I INPUT 1 -j "$INPUT_CHAIN"
  "$firewall" -I DOCKER-USER 1 -j "$DOCKER_CHAIN"

  # Migra com segurança a chain usada pela primeira versão deste controle.
  delete_jump "$firewall" INPUT "$LEGACY_CHAIN"
  delete_jump "$firewall" DOCKER-USER "$LEGACY_CHAIN"
  delete_chain "$firewall" "$LEGACY_CHAIN"
}

remove_family() {
  local firewall=$1

  delete_jump "$firewall" INPUT "$INPUT_CHAIN"
  delete_jump "$firewall" DOCKER-USER "$DOCKER_CHAIN"
  delete_jump "$firewall" INPUT "$LEGACY_CHAIN"
  delete_jump "$firewall" DOCKER-USER "$LEGACY_CHAIN"
  delete_chain "$firewall" "$INPUT_CHAIN"
  delete_chain "$firewall" "$DOCKER_CHAIN"
  delete_chain "$firewall" "$LEGACY_CHAIN"
}

apply_rules() {
  local firewall

  preflight
  for firewall in "${FIREWALL_BINARIES[@]}"; do
    apply_family "$firewall"
  done
  echo "Firewall Agenda aplicado em IPv4 e IPv6 na interface $LAN_INTERFACE."
}

remove_rules() {
  local firewall

  for firewall in "${FIREWALL_BINARIES[@]}"; do
    if [[ -x $firewall ]]; then
      remove_family "$firewall"
    fi
  done
  echo "Regras do firewall Agenda removidas."
}

require_root
case "${1:-}" in
  check)
    check_rules
    ;;
  apply)
    apply_rules
    ;;
  remove)
    remove_rules
    ;;
  *)
    echo "Uso: $0 {check|apply|remove}" >&2
    exit 2
    ;;
esac
