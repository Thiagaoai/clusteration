# clusteration

Nuvem de VPS/VMs.

# Cluster Proxmox `cluster-thiago`

## Painel Interno de VMs

Este repositório agora inclui um painel FastAPI em `app/` para criar e gerenciar VMs Proxmox com UI Jinja2/HTMX, worker in-process, terminal SSH/PTY via WebSocket e exposição opcional por subdomínio.

### Setup rápido

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Gere `SECRET_KEY`, hash da senha admin e chaves do console:

```bash
openssl rand -hex 32
python - <<'PY'
from passlib.context import CryptContext
print(CryptContext(schemes=["bcrypt"]).hash("troque-esta-senha"))
PY
ssh-keygen -t ed25519 -C "painel-console" -f /tmp/console_key -N ""
base64 -w 0 /tmp/console_key
cat /tmp/console_key.pub
rm /tmp/console_key /tmp/console_key.pub
```

Depois preencha `.env`, rode migrations e suba o app:

```bash
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

O healthcheck fica em `GET /health`; a UI fica em `/login`.

### Docker

O projeto inclui `Dockerfile`, `.dockerignore` e `docker-compose.yml`.

```bash
cp .env.example .env
$EDITOR .env
docker compose up -d --build
```

O container aplica migrations automaticamente no startup e sobe o FastAPI na porta `8000`.
Veja também `docs/deployment.md`.

Antes de criar VMs, valide o ambiente Proxmox:

```bash
source .venv/bin/activate
python scripts/panel-doctor.py
```

O painel também expõe `GET /api/readiness` autenticado. A criação de VM fica bloqueada com uma mensagem clara enquanto `PROXMOX_TOKEN_SECRET` e as chaves SSH do console não estiverem preenchidos.

### Exposure proxy opcional

```bash
API_INTERNAL_URL=http://127.0.0.1:8000 \
EXPOSURE_PROXY_SECRET=<mesmo .env> \
uvicorn app.exposure_proxy:app --host 0.0.0.0 --port 8080
```

Configure `*.<EXPOSURE_BASE_DOMAIN>` para apontar para esse proxy.

Kit operacional local para administrar o cluster Proxmox VE `cluster-thiago`.

Estado recebido em 2026-06-08:

- 4 nós Proxmox VE 9.2.3: `pve1`, `pve2`, `pve3`, `pve4`
- Rede: `10.1.10.0/24`, gateway `10.1.10.1`, DNS `1.1.1.1`
- GUI: `https://cluster.thiagaoai.online` ou `https://10.1.10.15:8006`
- Sem storage compartilhado; `local` e `local-lvm` são locais a cada nó
- Cluster vazio: 0 VMs, 0 containers
- Quorum 3/4: nunca reiniciar dois nós ao mesmo tempo

## Arquivos

- `docs/cluster-handoff.md`: handoff redigido, sem senha em claro
- `config/cluster.env.example`: variáveis para os scripts
- `config/ssh_config.example`: exemplo de acesso via jump host
- `scripts/cluster-health.sh`: checagem de saúde do cluster
- `scripts/rolling-upgrade.sh`: upgrade e reboot um nó por vez
- `scripts/configure-vzdump.sh`: cria agenda básica de backups
- `scripts/update-pve-certs.sh`: normaliza `search lan` e renova certificados PVE
- `scripts/rotate-root-password.sh`: troca senha root nos quatro nós
- `scripts/harden-ssh-key-only.sh`: desativa login SSH por senha depois da rotação
- `Dockerfile` / `docker-compose.yml`: build e execução em container
- `docs/deployment.md`: guia de deploy e variáveis obrigatórias

## Uso Rápido

Copie o arquivo de exemplo e preencha os dados locais:

```bash
cp config/cluster.env.example config/cluster.env
$EDITOR config/cluster.env
```

Carregue o ambiente e rode uma checagem:

```bash
source config/cluster.env
bash scripts/cluster-health.sh
```

Para operações com senha root, exporte a senha interativamente. Não salve a senha em arquivos:

```bash
read -rsp "Senha root atual: " PVE_ROOT_PASSWORD; echo
export PVE_ROOT_PASSWORD
```

## Ordem Recomendada

1. Confirmar acesso ao jump host e aos nós.
2. Rodar `bash scripts/cluster-health.sh`.
3. Trocar a senha root com `bash scripts/rotate-root-password.sh`.
4. Configurar backups com `bash scripts/configure-vzdump.sh`.
5. Atualizar certificados com `bash scripts/update-pve-certs.sh`.
6. Planejar 5º nó ou QDevice antes de depender do cluster.
7. Só depois considerar `bash scripts/harden-ssh-key-only.sh`, quando chaves de acesso externas estiverem validadas.

## Limites Atuais

Este workspace não contém credenciais de jump nem acesso confirmado aos nós. Os scripts foram preparados para execução quando esse acesso existir.
