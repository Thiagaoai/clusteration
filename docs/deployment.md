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

## Docker Compose

```bash
cp .env.example .env
$EDITOR .env
docker compose up -d --build
```

O container roda automaticamente:

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

