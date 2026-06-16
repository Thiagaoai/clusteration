#!/usr/bin/env bash
set -euo pipefail

USER_ID="${USER_ID:-panel@pve}"
TOKEN_ID="${TOKEN_ID:-clusteration}"
STORAGES="${STORAGES:-local-lvm local}"
ROTATE_TOKEN="${ROTATE_TOKEN:-0}"

if ! command -v pveum >/dev/null 2>&1; then
  echo "FAIL: rode este script dentro de um node Proxmox como root." >&2
  exit 1
fi

echo "== User ${USER_ID}"
pveum user add "${USER_ID}" --comment "Clusteration panel API user" 2>/dev/null || true

echo "== ACLs"
pveum aclmod / -user "${USER_ID}" -role PVEVMAdmin
pveum aclmod / -user "${USER_ID}" -role PVEAuditor
for storage in ${STORAGES}; do
  pveum aclmod "/storage/${storage}" -user "${USER_ID}" -role PVEDatastoreAdmin
done

if [[ "${ROTATE_TOKEN}" == "1" ]]; then
  echo "== Rotating token ${USER_ID}!${TOKEN_ID}"
  pveum user token remove "${USER_ID}" "${TOKEN_ID}" 2>/dev/null || true
fi

echo "== Token"
if ! pveum user token add "${USER_ID}" "${TOKEN_ID}" --privsep 0; then
  cat >&2 <<EOF

FAIL: o token ${USER_ID}!${TOKEN_ID} já existe ou não pôde ser criado.
Se você não tem mais o secret, rode:

  ROTATE_TOKEN=1 bash backend/scripts/configure-panel-token.sh

Depois coloque estes valores no Dokploy e redeploy:

  PROXMOX_TOKEN_ID=${USER_ID}!${TOKEN_ID}
  PROXMOX_TOKEN_SECRET=<value exibido uma única vez pelo Proxmox>

EOF
  exit 2
fi

cat <<EOF

OK. Copie para o Dokploy:

  PROXMOX_TOKEN_ID=${USER_ID}!${TOKEN_ID}
  PROXMOX_TOKEN_SECRET=<value exibido acima>

Use aspas simples se exportar no bash, porque o token id contém "!":

  export PROXMOX_TOKEN_ID='${USER_ID}!${TOKEN_ID}'

EOF
