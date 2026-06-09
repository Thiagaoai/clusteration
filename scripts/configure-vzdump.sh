#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

nodes_array

BACKUP_STORAGE="${BACKUP_STORAGE:-local}"
BACKUP_DAYS="${BACKUP_DAYS:-sun}"
BACKUP_START_TIME="${BACKUP_START_TIME:-02:00}"
BACKUP_MODE="${BACKUP_MODE:-snapshot}"
BACKUP_COMPRESS="${BACKUP_COMPRESS:-zstd}"
BACKUP_RETENTION="${BACKUP_RETENTION:-keep-last=3}"
BACKUP_ENABLED="${BACKUP_ENABLED:-1}"
JOB_ID="${BACKUP_JOB_ID:-local-weekly-all}"

info "Creating vzdump job ${JOB_ID} on cluster config"

cat <<EOF
Storage:   ${BACKUP_STORAGE}
Schedule:  ${BACKUP_DAYS} ${BACKUP_START_TIME}
Mode:      ${BACKUP_MODE}
Compress:  ${BACKUP_COMPRESS}
Retention: ${BACKUP_RETENTION}
Enabled:   ${BACKUP_ENABLED}
EOF

confirm "Apply backup job to /etc/pve/jobs.cfg?" || exit 0

remote_script="$(mktemp)"
cat >"${remote_script}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

job_id="$1"
storage="$2"
days="$3"
start_time="$4"
mode="$5"
compress="$6"
retention="$7"
enabled="$8"

jobs_file="/etc/pve/jobs.cfg"
tmp_file="$(mktemp)"

if [[ -f "${jobs_file}" ]]; then
  awk -v id "${job_id}" '
    /^vzdump:/ {
      split($0, parts, " ")
      if (skip && parts[2] != id) {
        skip=0
      }
      if (parts[2] == id) {
        skip=1
        next
      }
    }
    skip && /^[^[:space:]]/ { skip=0 }
    !skip { print }
  ' "${jobs_file}" > "${tmp_file}"
else
  : > "${tmp_file}"
fi

cat >> "${tmp_file}" <<JOB

vzdump: ${job_id}
    schedule ${days} ${start_time}
    enabled ${enabled}
    all 1
    storage ${storage}
    mode ${mode}
    compress ${compress}
    prune-backups ${retention}
JOB

install -m 0640 "${tmp_file}" "${jobs_file}"
rm -f "${tmp_file}"
EOF

scp_to_pve "${remote_script}" "${PVE_NODE_ARRAY[0]}" "/tmp/configure-vzdump-job.sh"
rm -f "${remote_script}"
ssh_pve "${PVE_NODE_ARRAY[0]}" "bash /tmp/configure-vzdump-job.sh '${JOB_ID}' '${BACKUP_STORAGE}' '${BACKUP_DAYS}' '${BACKUP_START_TIME}' '${BACKUP_MODE}' '${BACKUP_COMPRESS}' '${BACKUP_RETENTION}' '${BACKUP_ENABLED}' && rm -f /tmp/configure-vzdump-job.sh && cat /etc/pve/jobs.cfg"

info "Backup job configured"
