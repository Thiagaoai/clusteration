#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

if [[ -f "${PROJECT_ROOT}/config/cluster.env" ]]; then
  # shellcheck disable=SC1091
  source "${PROJECT_ROOT}/config/cluster.env"
fi

PVE_NODES="${PVE_NODES:-pve1 pve2 pve3 pve4}"
PVE_NODE_IPS="${PVE_NODE_IPS:-10.1.10.15 10.1.10.149 10.1.10.241 10.1.10.43}"
PVE_SSH_USER="${PVE_SSH_USER:-root}"
PVE_SSH_OPTS="${PVE_SSH_OPTS:--o BatchMode=yes -o ConnectTimeout=8}"

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '\n==> %s\n' "$*"
}

confirm() {
  local prompt="${1:-Continue?}"
  read -r -p "${prompt} [y/N] " answer
  [[ "${answer}" == "y" || "${answer}" == "Y" ]]
}

ssh_pve() {
  local host="$1"
  shift
  # shellcheck disable=SC2086
  ssh ${PVE_SSH_OPTS} "${PVE_SSH_USER}@${host}" "$@"
}

scp_to_pve() {
  local src="$1"
  local host="$2"
  local dst="$3"
  # shellcheck disable=SC2086
  scp ${PVE_SSH_OPTS} "${src}" "${PVE_SSH_USER}@${host}:${dst}"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

nodes_array() {
  # shellcheck disable=SC2206
  PVE_NODE_ARRAY=(${PVE_NODES})
}

node_ips_array() {
  # shellcheck disable=SC2206
  PVE_NODE_IP_ARRAY=(${PVE_NODE_IPS})
}
