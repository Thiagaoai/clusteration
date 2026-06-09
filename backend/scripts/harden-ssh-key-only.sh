#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

nodes_array

cat <<'EOF'
This disables SSH password login and keeps root login available by key.
Only run this after external key-based access has been tested through the jump host.
EOF

confirm "Disable SSH password authentication on all nodes?" || exit 0

for host in "${PVE_NODE_ARRAY[@]}"; do
  info "Hardening sshd on ${host}"
  ssh_pve "${host}" "cp -a /etc/ssh/sshd_config /etc/ssh/sshd_config.bak.\$(date +%Y%m%d%H%M%S); sed -i -E 's/^[#[:space:]]*PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config; if ! grep -q '^PasswordAuthentication ' /etc/ssh/sshd_config; then printf '\nPasswordAuthentication no\n' >> /etc/ssh/sshd_config; fi; sed -i -E 's/^[#[:space:]]*PermitRootLogin .*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config; if ! grep -q '^PermitRootLogin ' /etc/ssh/sshd_config; then printf '\nPermitRootLogin prohibit-password\n' >> /etc/ssh/sshd_config; fi; sshd -t; systemctl reload ssh"
done

info "SSH password authentication disabled"
