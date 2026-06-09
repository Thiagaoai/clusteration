#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

nodes_array

if [[ -z "${PVE_NEW_ROOT_PASSWORD:-}" ]]; then
  read -rsp "New root password: " PVE_NEW_ROOT_PASSWORD
  echo
  read -rsp "Confirm new root password: " PVE_NEW_ROOT_PASSWORD_CONFIRM
  echo
  [[ "${PVE_NEW_ROOT_PASSWORD}" == "${PVE_NEW_ROOT_PASSWORD_CONFIRM}" ]] || die "Passwords do not match"
fi

[[ -n "${PVE_NEW_ROOT_PASSWORD}" ]] || die "New password is empty"

cat <<'EOF'
This changes the Linux root password on every Proxmox node.
Make sure at least one existing SSH session remains open until verification completes.
EOF

confirm "Rotate root password on all nodes?" || exit 0

for host in "${PVE_NODE_ARRAY[@]}"; do
  info "Rotating password on ${host}"
  ssh_pve "${host}" "chpasswd" <<<"root:${PVE_NEW_ROOT_PASSWORD}"
done

unset PVE_NEW_ROOT_PASSWORD
info "Root password rotation complete. Verify GUI and SSH login before closing existing sessions."
