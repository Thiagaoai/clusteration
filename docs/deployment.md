# Deployment

## Variáveis obrigatórias

Copie `.env.example` para `.env` e preencha:

- `SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH`
- `DATABASE_URL`
- `PROXMOX_HOST`
- `PROXMOX_TOKEN_ID`
- `PROXMOX_TOKEN_SECRET`
- `PROXMOX_DEFAULT_NODE`
- `CONSOLE_SSH_PRIVATE_KEY`
- `CONSOLE_SSH_PUBLIC_KEY`

Nunca versionar `.env`.

## Estrutura para Dokploy (serviço único)

O painel é **um serviço só**: o backend FastAPI serve a API (`/api`), o WebSocket
do terminal (`/terminal/ws`) **e** o frontend estático (SPA em `backend/app/web/`).
Não há mais proxy nginx separado nem comunicação entre containers — por isso não
existe mais 502/erro de rota entre serviços.

### Deploy como Dockerfile (recomendado)

No Dokploy, crie **um** app apontando para o repositório:

- Build type: Dockerfile
- Build context / Root Directory: `backend`
- Dockerfile path: `Dockerfile` (relativo ao contexto `backend`)
- Porta interna: `8000`
- Healthcheck: `/health`
- Em **Domains**, aponte seu domínio (ex.: `app.thiagao.online`) para esse app,
  porta `8000`.
- Em **Advanced → Volumes**, monte um volume em `/data` para persistir o SQLite.

Sem esse volume, qualquer rebuild/redeploy recria o container e o painel volta
sem inventário, jobs, senha alterada e histórico local. Em produção, mantenha:

```bash
DATABASE_URL=sqlite+aiosqlite:////data/vmpanel.db
BACKUP_DIR=/data/backups
```

O endpoint autenticado `GET /api/system/status` mostra se o banco atual está em
storage durável. `database.durable=false` significa risco real de reset.

### Ou via Docker Compose

Crie um serviço **Docker Compose** apontando para `docker-compose.yml`. Ele tem um
único serviço `app` (porta `8000`) com o volume `panel-data:/data`. Aponte o
domínio para o serviço `app`, porta `8000`.

Variáveis (aba Environment, em qualquer um dos dois modos):

```bash
ENVIRONMENT=production
SECRET_KEY=...
SESSION_SAME_SITE=strict
SESSION_HTTPS_ONLY=true
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=...
DATABASE_URL=sqlite+aiosqlite:////data/vmpanel.db
BACKUP_DIR=/data/backups
PROXMOX_HOST=https://10.1.10.209:8006
PROXMOX_TOKEN_ID=...
PROXMOX_TOKEN_SECRET=...
PROXMOX_DEFAULT_NODE=pve
CONSOLE_SSH_PRIVATE_KEY=...
CONSOLE_SSH_PUBLIC_KEY=...
TEMPLATE_DEBIAN_VMID=9000
TEMPLATE_UBUNTU_VMID=9001
TEMPLATE_FEDORA_VMID=9002
TEMPLATE_HERMES_VMID=9010
TEMPLATE_OPENCLAW_VMID=9011
TEMPLATE_CLAUDE_VMID=9012
```

Para produção mais robusta, use Postgres apontando `DATABASE_URL` para
`postgresql+asyncpg://...` (o `asyncpg` já está nas dependências).

## Arquivos que precisam estar no Git

```text
backend/Dockerfile
backend/.dockerignore
backend/requirements.txt
backend/alembic.ini
backend/alembic/
backend/app/
backend/app/web/        # SPA (index.html, css, js, img) servido pelo FastAPI
backend/config/
backend/scripts/
pyproject.toml
docker-compose.yml
.env.example
.gitignore
.dockerignore
docs/
README.md
```

Não versionar:

```text
.env
vmpanel.db
.venv/
__pycache__/
backend/config/cluster.env
backend/config/ssh_config
```

## Docker Compose

```bash
cp .env.example .env
$EDITOR .env
docker compose up -d --build
```

O backend roda automaticamente:

```bash
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Healthcheck

```bash
curl http://127.0.0.1:8000/health
```

## Validar Proxmox

Dentro do ambiente com variáveis carregadas:

```bash
python scripts/panel-doctor.py
```

## Templates cloud-init

O painel espera templates no Proxmox:

- Debian: VMID `9000`
- Ubuntu: VMID `9001`
- Fedora: VMID `9002`
- Hermes AI image: VMID `9010`
- OpenClaw AI image: VMID `9011`
- Claude CLI image: VMID `9012`

Eles devem existir no node configurado em `PROXMOX_DEFAULT_NODE` e estar marcados como template.

Para criar ou recriar esses templates no nó Proxmox:

```bash
cd backend
sudo bash scripts/build-cloudinit-templates.sh
```

Para substituir VMIDs já existentes:

```bash
sudo REPLACE_EXISTING=1 bash scripts/build-cloudinit-templates.sh
```

As imagens AI usam Ubuntu como base e aceitam overrides de instalação:

```bash
sudo REPLACE_EXISTING=1 \
  HERMES_MODEL=hermes3 \
  OPENCLAW_INSTALL_CMD='npm install -g openclaw@latest' \
  CLAUDE_INSTALL_CMD='npm install -g @anthropic-ai/claude-code@latest' \
  bash scripts/build-cloudinit-templates.sh
```

## Reinstalar VPS

O painel expõe `POST /api/vms/{id}/reinstall` e um botão **Reinstalar** no
inventário. Esse fluxo é destrutivo: exige digitar o hostname, escolher o
template e informar uma nova senha root. O job apaga a VM atual no Proxmox,
clona o template escolhido, reconfigura cloud-init, reinicia para obter lease
DHCP único e re-checa SSH. A ação fica no audit log como `vm.reinstall`.
