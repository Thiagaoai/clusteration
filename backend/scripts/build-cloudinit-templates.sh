#!/usr/bin/env bash
set -euo pipefail

# Build Proxmox cloud-init templates used by the panel.
# Run on a Proxmox node as root. Existing VMIDs are kept unless
# REPLACE_EXISTING=1 is set.

STORAGE="${STORAGE:-local-lvm}"
BRIDGE="${BRIDGE:-vmbr0}"
WORKDIR="${WORKDIR:-/var/lib/vz/template/clusteration-cloud}"
REPLACE_EXISTING="${REPLACE_EXISTING:-0}"

DEBIAN_VMID="${TEMPLATE_DEBIAN_VMID:-9000}"
UBUNTU_VMID="${TEMPLATE_UBUNTU_VMID:-9001}"
FEDORA_VMID="${TEMPLATE_FEDORA_VMID:-9002}"
HERMES_VMID="${TEMPLATE_HERMES_VMID:-9010}"
OPENCLAW_VMID="${TEMPLATE_OPENCLAW_VMID:-9011}"
CLAUDE_VMID="${TEMPLATE_CLAUDE_VMID:-9012}"

DEBIAN_URL="${DEBIAN_URL:-https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2}"
UBUNTU_URL="${UBUNTU_URL:-https://cloud-images.ubuntu.com/releases/resolute/release/ubuntu-26.04-server-cloudimg-amd64.img}"
FEDORA_VERSION="${FEDORA_VERSION:-44}"
FEDORA_URL="${FEDORA_URL:-https://download.fedoraproject.org/pub/fedora/linux/releases/${FEDORA_VERSION}/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-${FEDORA_VERSION}-1.1.x86_64.qcow2}"

HERMES_INSTALL_CMD="${HERMES_INSTALL_CMD:-curl -fsSL https://ollama.com/install.sh | sh}"
HERMES_MODEL="${HERMES_MODEL:-hermes3}"
OPENCLAW_INSTALL_CMD="${OPENCLAW_INSTALL_CMD:-npm install -g openclaw@latest}"
CLAUDE_INSTALL_CMD="${CLAUDE_INSTALL_CMD:-npm install -g @anthropic-ai/claude-code@latest}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "missing required command: $1" >&2
    exit 1
  }
}

download() {
  local url="$1"
  local dest="$2"
  mkdir -p "$(dirname "$dest")"
  if [[ -f "$dest" ]]; then
    echo "using cached image: $dest"
    return
  fi
  echo "downloading $url"
  local tmp="${dest}.tmp"
  if command -v curl >/dev/null 2>&1; then
    curl -fL "$url" -o "$tmp"
  else
    wget -O "$tmp" "$url"
  fi
  mv "$tmp" "$dest"
}

vmid_exists() {
  qm status "$1" >/dev/null 2>&1
}

prepare_vmid() {
  local vmid="$1"
  if ! vmid_exists "$vmid"; then
    return
  fi
  if [[ "$REPLACE_EXISTING" != "1" ]]; then
    echo "VMID $vmid already exists; set REPLACE_EXISTING=1 to rebuild it" >&2
    exit 1
  fi
  echo "destroying existing VMID $vmid"
  qm stop "$vmid" >/dev/null 2>&1 || true
  qm destroy "$vmid" --purge 1 --destroy-unreferenced-disks 1
}

customize_common() {
  local image="$1"
  local family="$2"
  if ! command -v virt-customize >/dev/null 2>&1; then
    echo "virt-customize not found; skipping offline package injection for $image"
    echo "install libguestfs-tools on the Proxmox node for fully prebuilt images"
    return
  fi
  virt-customize -a "$image" \
    --run-command 'if command -v apt-get >/dev/null 2>&1; then apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y qemu-guest-agent openssh-server cloud-init curl git ca-certificates python3 python3-pip python3-venv nodejs npm; fi' \
    --run-command 'if command -v dnf >/dev/null 2>&1; then dnf install -y qemu-guest-agent openssh-server cloud-init curl git ca-certificates python3 python3-pip nodejs npm; fi' \
    --run-command 'systemctl enable qemu-guest-agent >/dev/null 2>&1 || true' \
    --run-command 'systemctl enable ssh >/dev/null 2>&1 || systemctl enable sshd >/dev/null 2>&1 || true' \
    --run-command "echo clusteration-template-${family} >/etc/clusteration-template"
}

customize_ai() {
  local image="$1"
  local bundle="$2"
  customize_common "$image" "$bundle"
  if ! command -v virt-customize >/dev/null 2>&1; then
    return
  fi
  case "$bundle" in
    hermes)
      virt-customize -a "$image" \
        --run-command "$HERMES_INSTALL_CMD" \
        --run-command "mkdir -p /opt/clusteration && printf '%s\n' 'HERMES_MODEL=${HERMES_MODEL}' >/opt/clusteration/ai.env"
      ;;
    openclaw)
      virt-customize -a "$image" --run-command "$OPENCLAW_INSTALL_CMD"
      ;;
    claude)
      virt-customize -a "$image" --run-command "$CLAUDE_INSTALL_CMD"
      ;;
  esac
}

create_template() {
  local vmid="$1"
  local name="$2"
  local image="$3"
  local os_type="${4:-l26}"
  prepare_vmid "$vmid"
  echo "creating template $name ($vmid)"
  qm create "$vmid" \
    --name "$name" \
    --memory 2048 \
    --cores 2 \
    --net0 "virtio,bridge=${BRIDGE}" \
    --ostype "$os_type" \
    --scsihw virtio-scsi-pci \
    --agent enabled=1 \
    --serial0 socket \
    --vga serial0
  qm importdisk "$vmid" "$image" "$STORAGE"
  local disk_ref
  disk_ref="$(qm config "$vmid" | awk '/^unused0:/{print $2}')"
  if [[ -z "$disk_ref" ]]; then
    echo "could not find imported disk for VMID $vmid" >&2
    exit 1
  fi
  qm set "$vmid" --scsi0 "$disk_ref"
  qm set "$vmid" --ide2 "${STORAGE}:cloudinit"
  qm set "$vmid" --boot c --bootdisk scsi0
  qm set "$vmid" --ipconfig0 ip=dhcp
  qm set "$vmid" --ciuser root
  qm template "$vmid"
}

build_base() {
  local os="$1"
  local vmid="$2"
  local name="$3"
  local url="$4"
  local ext="${url##*.}"
  local source="${WORKDIR}/${os}.${ext}"
  local image="${WORKDIR}/${os}-custom.${ext}"
  download "$url" "$source"
  cp -f "$source" "$image"
  customize_common "$image" "$os"
  create_template "$vmid" "$name" "$image"
}

build_ai() {
  local bundle="$1"
  local vmid="$2"
  local name="$3"
  local source="${WORKDIR}/ubuntu.img"
  local image="${WORKDIR}/${bundle}-custom.img"
  download "$UBUNTU_URL" "$source"
  cp -f "$source" "$image"
  customize_ai "$image" "$bundle"
  create_template "$vmid" "$name" "$image"
}

main() {
  [[ "$(id -u)" == "0" ]] || {
    echo "run as root on a Proxmox node" >&2
    exit 1
  }
  need qm
  need awk
  command -v curl >/dev/null 2>&1 || need wget

  mkdir -p "$WORKDIR"
  build_base debian "$DEBIAN_VMID" debian-13-cloudinit-template "$DEBIAN_URL"
  build_base ubuntu "$UBUNTU_VMID" ubuntu-2604-cloudinit-template "$UBUNTU_URL"
  build_base fedora "$FEDORA_VMID" fedora-44-cloudinit-template "$FEDORA_URL"
  build_ai hermes "$HERMES_VMID" hermes-ai-template
  build_ai openclaw "$OPENCLAW_VMID" openclaw-ai-template
  build_ai claude "$CLAUDE_VMID" claude-cli-template
}

main "$@"
