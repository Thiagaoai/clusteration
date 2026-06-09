# Handoff Redigido — Cluster Proxmox `cluster-thiago`

Documento operacional sem senha em claro. A senha original do handoff deve ser trocada na entrega e guardada em gestor de segredos.

## TL;DR

- Cluster `cluster-thiago`, 4 nós Proxmox VE 9.2.3.
- Rede `10.1.10.0/24`, gateway `10.1.10.1`, DNS `1.1.1.1`.
- GUI: `https://cluster-thiagao.dockplusai.io` ou `https://10.1.10.15:8006`.
- Login atual: `root@pam`; senha sensível removida deste repositório.
- Hardening atual: `fail2ban` ativo nos 4 nós, firewall Proxmox desligado, SSH por senha ligado.
- Quorum 3/4: tolera apenas uma falha. Não reiniciar dois nós ao mesmo tempo.
- Cluster vazio: 0 VMs, 0 containers.

## Nós

| Nó | IP | CPU | RAM | Disco principal | `local-lvm` | Observação |
|----|----|-----|-----|-----------------|-------------|------------|
| `pve1` | `10.1.10.15` | i5-10500 | 16GB | NVMe Samsung 256G | 141G | mini-PC |
| `pve2` | `10.1.10.149` | i7-8700 | 16GB | HDD Seagate 1TB | 794G | disco lento, bom para bulk/backup |
| `pve3` | `10.1.10.241` | i5-10500 | 16GB | NVMe Samsung 256G | 141G | mini-PC |
| `pve4` | `10.1.10.43` | i5-10500T | 16GB | NVMe WDC SN730 256G | 141G | CPU low-power, 1 slot RAM livre |

## Rede

- Bridge de VMs: `vmbr0`.
- Porta física: `nic0`.
- `/etc/hosts` esperado:

```text
10.1.10.15  pve1.lan pve1
10.1.10.149 pve2.lan pve2
10.1.10.241 pve3.lan pve3
10.1.10.43  pve4.lan pve4
```

## Cluster

- Corosync `knet`, `link_mode: passive`, `secauth: on`.
- `config_version: 4`.
- `expected votes: 4`, quorum `3`.

## Storage

```text
dir: local
    path /var/lib/vz
    content iso,vztmpl,backup,import
lvmthin: local-lvm
    thinpool data, vgname pve
    content rootdir,images
```

Sem storage compartilhado. Migração ao vivo e HA real não estão disponíveis.

## Segurança Atual

- `fail2ban`: jails `sshd` e `proxmox`.
- `ignoreip`: `127.0.0.1/8 ::1 10.1.10.0/24 10.1.10.210`.
- Firewall Proxmox desligado.
- SSH root por senha habilitado.
- Chave SSH mesh entre nós configurada.

## Pendências

- Trocar senha root.
- Confirmar credenciais do jump `23.25.234.65` / `23.25.234.66`.
- Configurar backups.
- Normalizar certificados GUI.
- Adicionar 5º nó ou QDevice.
- Avaliar storage compartilhado, firewall Proxmox e SSH key-only.
