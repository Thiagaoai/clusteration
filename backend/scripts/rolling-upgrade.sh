#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

nodes_array

info "Preflight quorum check"
ssh_pve "${PVE_NODE_ARRAY[0]}" "pvecm status"

cat <<'EOF'

This will upgrade and reboot nodes one at a time.
With a 4-node cluster and quorum 3, do not start this if any node is already down.
EOF

confirm "Proceed with rolling upgrade?" || exit 0

for host in "${PVE_NODE_ARRAY[@]}"; do
  info "Upgrading ${host}"
  ssh_pve "${host}" "apt update && DEBIAN_FRONTEND=noninteractive apt -y dist-upgrade"

  if confirm "Reboot ${host} now?"; then
    ssh_pve "${host}" "systemctl reboot" || true
    info "Waiting for ${host} to go down"
    sleep 10
    info "Waiting for ${host} to return"
    until ssh_pve "${host}" "true" >/dev/null 2>&1; do
      sleep 10
    done
    ssh_pve "${host}" "pveversion"
  fi

  info "Checking quorum after ${host}"
  ssh_pve "${PVE_NODE_ARRAY[0]}" "pvecm status"
  confirm "Continue to next node?" || exit 0
done

info "Rolling upgrade complete"
