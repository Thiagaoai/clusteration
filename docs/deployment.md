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
APP_BUILD_ID=...
SECRET_KEY=...
SESSION_SAME_SITE=strict
SESSION_HTTPS_ONLY=true
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=...
DATABASE_URL=sqlite+aiosqlite:////data/vmpanel.db
BACKUP_DIR=/data/backups
PROXMOX_HOST=https://10.1.10.15:8006
PROXMOX_TOKEN_ID=...
PROXMOX_TOKEN_SECRET=...
PROXMOX_DEFAULT_NODE=pve1
CONSOLE_SSH_PRIVATE_KEY=...
CONSOLE_SSH_PUBLIC_KEY=...
TERMINAL_SESSION_TTL_SECONDS=300
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

Para confirmar que o Dokploy está servindo o build novo, use:

```bash
curl https://app.thiagao.online/version
```

O campo `build` deve mudar a cada rebuild/deploy. No Dokploy, defina
`APP_BUILD_ID` com o commit ou identificador do deploy quando quiser rastreio
exato.

## Validar Proxmox

Dentro do ambiente com variáveis carregadas:

```bash
python scripts/panel-doctor.py
```

No painel autenticado, use também `GET /api/system/proxmox` ou o botão
**Validar Proxmox** na tela inicial. Ele confirma API, storage e templates sem
expor secrets.

## Token Proxmox

No shell de um node Proxmox, configure o usuário/token do painel com roles
built-in válidas:

```bash
bash backend/scripts/configure-panel-token.sh
```

Se o token já existir e o secret tiver sido perdido, rotacione:

```bash
ROTATE_TOKEN=1 bash backend/scripts/configure-panel-token.sh
```

Depois coloque no Dokploy:

```bash
PROXMOX_TOKEN_ID=panel@pve!clusteration
PROXMOX_TOKEN_SECRET=<value exibido uma única vez pelo Proxmox>
```

Se for testar em bash/zsh, use aspas simples no token id por causa do `!`:

```bash
export PROXMOX_TOKEN_ID='panel@pve!clusteration'
```

Não use `VM.Monitor` em custom role nesse cluster; o Proxmox recusou esse
privilégio e a role não foi criada. O script usa `PVEVMAdmin`, `PVEAuditor` e
`PVEDatastoreAdmin` para manter a criação, config, resize, start/stop/delete e
leitura de templates funcionando.

## Templates cloud-init

O painel espera templates no Proxmox:

- Debian: VMID `9000`
- Ubuntu: VMID `9001`
- Fedora: VMID `9002`
- Hermes AI image: VMID `9010`
- OpenClaw AI image: VMID `9011`
- Claude CLI image: VMID `9012`

Eles devem existir em algum node do cluster e estar marcados como template. Como
esse cluster usa storage local por node, mantenha `PROXMOX_DEFAULT_NODE=pve1`
quando os templates estiverem em `pve1`. O backend também tenta localizar o node
real do template pelo VMID antes de clonar, para evitar falhas causadas por
`pve`/`pve1` errado.

Para criar ou recriar esses templates no nó Proxmox:

```bash
cd backend
sudo bash scripts/build-cloudinit-templates.sh
```

Por padrão, o script pula VMIDs que já existem. Para construir só uma parte dos
templates, use `TEMPLATE_FILTER` com os nomes separados por vírgula:

```bash
sudo TEMPLATE_FILTER=fedora,hermes,openclaw,claude \
  bash scripts/build-cloudinit-templates.sh
```

Para substituir VMIDs já existentes:

```bash
sudo REPLACE_EXISTING=1 bash scripts/build-cloudinit-templates.sh
```

As imagens AI usam Ubuntu como base. O script expande a imagem para `16G`
antes da instalação offline dos pacotes; ajuste com `AI_IMAGE_SIZE` se precisar.
O release da imagem Fedora pode ser sobrescrito com `FEDORA_IMAGE_RELEASE`.
O painel nunca tenta reduzir disco no Proxmox: se o template já tiver 16GB e a
requisição vier com 12GB, a VM sobe com 16GB e o job registra o ajuste.

As imagens AI aceitam overrides de instalação:

```bash
sudo REPLACE_EXISTING=1 \
  AI_IMAGE_SIZE=16G \
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
