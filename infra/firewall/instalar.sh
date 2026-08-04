#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "ERRO: execute este instalador com sudo." >&2
  exit 1
fi

readonly SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly TARGET_SCRIPT=/usr/local/sbin/agenda-docker-firewall
readonly TARGET_UNIT=/etc/systemd/system/agenda-docker-firewall.service
readonly TARGET_DOC_DIR=/usr/local/share/doc/agenda-firewall

bash -n "$SOURCE_DIR/agenda-docker-firewall.sh"
bash "$SOURCE_DIR/agenda-docker-firewall.sh" check

install -o root -g root -m 0755 \
  "$SOURCE_DIR/agenda-docker-firewall.sh" \
  "$TARGET_SCRIPT"
install -o root -g root -m 0644 \
  "$SOURCE_DIR/agenda-docker-firewall.service" \
  "$TARGET_UNIT"
install -d -o root -g root -m 0755 "$TARGET_DOC_DIR"
install -o root -g root -m 0644 "$SOURCE_DIR/README.md" "$TARGET_DOC_DIR/README.md"

systemd-analyze verify "$TARGET_UNIT"
systemctl daemon-reload
systemctl enable agenda-docker-firewall.service
systemctl restart agenda-docker-firewall.service

echo
systemctl --no-pager --full status agenda-docker-firewall.service
