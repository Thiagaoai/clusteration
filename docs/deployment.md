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

## Opção A (recomendada): deploy único via Docker Compose

É a forma mais simples e à prova de erro de rede: o frontend fala com o backend
pelo nome de serviço `backend` automaticamente (mesma rede do stack), sem
precisar adivinhar hostname interno.

No Dokploy:

1. Crie um serviço do tipo **Docker Compose** apontando para este repositório.
2. Compose path: `docker-compose.yml`.
3. Na aba **Environment**, preencha as variáveis do backend (veja a lista
   abaixo). O Compose injeta elas via `${VAR}`.
4. Em **Domains**, aponte seu domínio (ex.: `app.thiagao.online`) para o serviço
   **`frontend`**, porta `80`.

O `BACKEND_URL` do frontend já vem fixo como `http://backend:8000` no
`docker-compose.yml`, então não precisa configurar nada extra de rede.

Variáveis (aba Environment do Compose):

```bash
SECRET_KEY=...
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=...
DATABASE_URL=sqlite+aiosqlite:////data/vmpanel.db
PROXMOX_HOST=https://10.1.10.209:8006
PROXMOX_TOKEN_ID=...
PROXMOX_TOKEN_SECRET=...
PROXMOX_DEFAULT_NODE=pve
CONSOLE_SSH_PRIVATE_KEY=...
CONSOLE_SSH_PUBLIC_KEY=...
```

Para persistir o SQLite entre deploys, o volume `panel-data:/data` já está no
compose. (Para produção mais robusta, use Postgres apontando `DATABASE_URL` para
`postgresql+asyncpg://...`.)

## Opção B: dois apps separados (Dockerfile)

Crie dois apps apontando para o mesmo repositório GitHub. Os dois precisam estar
na **mesma rede** (`dokploy-network`, padrão para Applications; não use *Isolated
Deployments*), e o frontend precisa do **nome de serviço interno do backend**.

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

Variável do frontend (use o **nome de serviço interno** do app backend, que
aparece nas configurações/logs do Dokploy — ex.: `clusteration-clusterationbackend-faaijc`):

```bash
BACKEND_URL=http://<nome-do-servico-backend>:8000
```

Se aparecer **502** em `/api/...`, é porque o `BACKEND_URL` não está resolvendo o
backend. Confirme o nome do serviço e que ambos os apps estão na `dokploy-network`.
Na dúvida, use a **Opção A (Compose)**, que elimina esse problema.

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

