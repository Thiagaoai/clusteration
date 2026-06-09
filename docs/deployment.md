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

## Estrutura para Dokploy

O repositório está separado em dois serviços **autossuficientes**, cada um com
seu próprio contexto de build (a pasta do serviço):

- `backend/`: backend FastAPI completo (código em `backend/app/`, migrations em
  `backend/alembic/`, `backend/requirements.txt`, etc.).
- `frontend/`: frontend estático Nginx (HTML/CSS/JS em `frontend/`).

No Dokploy, crie dois apps apontando para o mesmo repositório GitHub:

### Backend

- Build type: Dockerfile
- Build context / Root Directory: `backend`
- Dockerfile path: `Dockerfile` (relativo ao contexto `backend`)
- Porta interna: `8000`
- Healthcheck: `/health`

Variáveis principais do backend:

```bash
ENVIRONMENT=production
SECRET_KEY=...
SESSION_SAME_SITE=lax
SESSION_HTTPS_ONLY=true
DATABASE_URL=sqlite+aiosqlite:////data/vmpanel.db
PROXMOX_HOST=...
PROXMOX_TOKEN_ID=...
PROXMOX_TOKEN_SECRET=...
CONSOLE_SSH_PRIVATE_KEY=...
CONSOLE_SSH_PUBLIC_KEY=...
```

Se o frontend estiver em outro domínio, configure também:

```bash
CORS_ORIGINS=https://seu-frontend.example.com
SESSION_SAME_SITE=none
SESSION_HTTPS_ONLY=true
```

### Frontend

- Build type: Dockerfile
- Build context / Root Directory: `frontend`
- Dockerfile path: `Dockerfile` (relativo ao contexto `frontend`)
- Porta interna: `80`

Variável do frontend:

```bash
BACKEND_URL=http://nome-do-servico-backend:8000
```

Quando frontend e backend estão na mesma rede interna do Dokploy, use o host interno do serviço backend. O Nginx do frontend faz proxy de `/api` e `/terminal/ws` para esse backend.

## Arquivos que precisam estar no Git

```text
backend/Dockerfile
backend/.dockerignore
backend/requirements.txt
backend/alembic.ini
backend/alembic/
backend/app/
backend/config/
backend/scripts/
frontend/Dockerfile
frontend/nginx.conf
frontend/index.html
frontend/css/
frontend/js/
frontend/img/
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

Eles devem existir no node configurado em `PROXMOX_DEFAULT_NODE` e estar marcados como template.

