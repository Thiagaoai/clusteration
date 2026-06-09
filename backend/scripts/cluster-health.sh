#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

nodes_array
node_ips_array

info "SSH reachability"
for host in "${PVE_NODE_ARRAY[@]}"; do
  printf '%-6s ' "${host}"
  if ssh_pve "${host}" "hostname && pveversion" 2>/dev/null; then
    true
  else
    printf 'unreachable\n'
  fi
done

info "Cluster status"
ssh_pve "${PVE_NODE_ARRAY[0]}" "pvecm status && printf '\n' && pvecm nodes"

info "Corosync links"
ssh_pve "${PVE_NODE_ARRAY[0]}" "corosync-cfgtool -n"

info "Guests per node"
for host in "${PVE_NODE_ARRAY[@]}"; do
  printf '\n-- %s --\n' "${host}"
  ssh_pve "${host}" "qm list; printf '\n'; pct list"
done

info "Storage"
ssh_pve "${PVE_NODE_ARRAY[0]}" "pvesm status"

info "fail2ban"
for host in "${PVE_NODE_ARRAY[@]}"; do
  printf '\n-- %s --\n' "${host}"
  ssh_pve "${host}" "systemctl is-active fail2ban; fail2ban-client status || true"
done

info "Firewall status"
for host in "${PVE_NODE_ARRAY[@]}"; do
  printf '\n-- %s --\n' "${host}"
  ssh_pve "${host}" "pve-firewall status || true"
done
