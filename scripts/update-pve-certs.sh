#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

nodes_array

cat <<'EOF'
This normalizes the resolver search domain to "lan", regenerates PVE certificates,
and restarts pveproxy on each node.
EOF

confirm "Proceed with certificate refresh?" || exit 0

for host in "${PVE_NODE_ARRAY[@]}"; do
  info "Updating ${host}"
  ssh_pve "${host}" "cp -a /etc/resolv.conf /etc/resolv.conf.bak.\$(date +%Y%m%d%H%M%S); if grep -q '^search ' /etc/resolv.conf; then sed -i 's/^search .*/search lan/' /etc/resolv.conf; else printf '\nsearch lan\n' >> /etc/resolv.conf; fi; pvecm updatecerts -f; systemctl restart pveproxy"
done

info "Certificates refreshed"
