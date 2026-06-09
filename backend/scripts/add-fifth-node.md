# Adicionar 5º Nó ao `cluster-thiago`

Use este runbook quando o novo hardware/IP estiver confirmado.

## Pré-requisitos

- Proxmox VE na mesma versão dos nós existentes.
- Hostname definitivo configurado antes de entrar no cluster.
- IP fixo na `10.1.10.0/24`.
- DNS/gateway corretos.
- SSH root funcionando a partir de `pve1`.
- Nó novo sem VMs/CTs e sem cluster anterior.

## No Nó Novo

```bash
apt update && apt -y dist-upgrade
hostnamectl set-hostname pve5
```

Garanta `/etc/hosts` com todos os nós:

```text
10.1.10.15  pve1.lan pve1
10.1.10.149 pve2.lan pve2
10.1.10.241 pve3.lan pve3
10.1.10.43  pve4.lan pve4
10.1.10.X   pve5.lan pve5
```

## Entrar no Cluster

No nó novo:

```bash
pvecm add 10.1.10.15 --link0 10.1.10.X --use_ssh
```

## Verificação

Em qualquer nó existente:

```bash
pvecm status
pvecm nodes
corosync-cfgtool -n
```

O cluster com 5 nós terá quorum 3 e melhora a tolerância a falhas em relação ao estado atual de 4 nós.
