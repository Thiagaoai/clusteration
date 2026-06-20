# Clusteration deploy audit - 2026-06-20

## Verdict

The Proxmox `/config` failure has been fixed in the repository, but production
traffic for `app.thiagao.online` is still served by an old runtime.

Current production evidence:

```bash
curl -fsS https://app.thiagao.online/version
```

```json
{"status":"ok","build":"unknown","environment":"production"}
```

Expected runtime marker:

```text
2026-06-20-dokploy-runtime-proof-v3
```

Current GitHub `main`:

```text
77e17cc Harden Dokploy runtime repair script
```

## What is fixed in code

- Template node resolution now prefers Proxmox `/cluster/resources`, so cloning
  no longer depends on `GET /nodes/<node>/qemu/<template>/config`.
- Template disk size now prefers `maxdisk` from `/cluster/resources`.
- If `/config` or disk resize is denied, VM provisioning continues with the
  template disk instead of failing the whole create.
- Error rows that never received a Proxmox VMID can be retried from the UI.
- Dockerfiles contain build guards that fail stale source builds.
- Runtime logs include `CLUSTERATION_RUNTIME build=...` on startup.

Verification:

```bash
PYTHONPATH=backend .venv/bin/python -m unittest discover -s tests -v
node --check backend/app/web/js/app.js
python3 -m py_compile backend/scripts/dokploy-repair.py backend/app/main.py backend/app/core/config.py
```

The Python suite currently passes `9/9`.

## What production is actually serving

Production static assets match the older commit `b6e9c57`:

```text
prod index.html  7d3b322bef7a7d7715f7567e8d62377f276e990e4c1e7da78cc3b70839d461f4
prod app.js      bb254602a7d4f517628fe09179f8fecd08656aafb579aa1b77ff04d6b04c8994
prod app.css     55e898e5254aed104a1024d9f3c22a6e082a7b15ce8c796fe592b12f1045a5e9
```

Those hashes are the files at:

```text
b6e9c57 Stabilize Proxmox provisioning and terminal sessions
```

So the current public route is not serving the current image from `main`.

## Deploy attempts already made

The Dokploy webhook accepted deploy payloads for the current branch:

```json
{"message":"Application deployed successfully"}
```

After the webhook response, repeated public checks still returned:

```json
{"status":"ok","build":"unknown","environment":"production"}
```

This proves the webhook/build path alone is not replacing the active runtime.

## Network and access checks

- `app.thiagao.online` resolves through the server at `23.25.234.77`.
- Public app ports `8000`, `8001`, and `8080` are not reachable directly.
- HTTP `80` redirects through Traefik to HTTPS.
- HTTPS `443` serves the old Uvicorn app through Traefik.
- `https://app.thiagao.online/api/system/status` returns `401` without admin session.
- `http://23.25.234.77:3000/api/project.all` returns `401` without `x-api-key`.
- SSH to `23.25.234.77` with the available local keys is denied.

## Required repair

Use the Dokploy API key for the instance at `http://23.25.234.77:3000`:

```bash
export DOKPLOY_API_KEY=<token>
python backend/scripts/dokploy-repair.py --repair --restart --clean-queues --logs --wait 300
```

Or add the same value as a GitHub Actions repository secret named
`DOKPLOY_API_KEY`, then run the manual workflow:

```text
Actions -> Dokploy runtime repair -> Run workflow
```

Success criteria:

```bash
curl -fsS https://app.thiagao.online/version
```

must return:

```json
{"status":"ok","build":"2026-06-20-dokploy-runtime-proof-v3","environment":"production"}
```

and app logs must contain:

```text
CLUSTERATION_RUNTIME build=2026-06-20-dokploy-runtime-proof-v3
```

## Manual server repair if API key is unavailable

Run these on the Dokploy server with shell access:

```bash
docker ps --format 'table {{.ID}}\t{{.Image}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -i clusteration
docker logs --tail=200 <clusteration-container>
docker stop <old-clusteration-container>
docker rm <old-clusteration-container>
docker restart dokploy-traefik
```

Then redeploy the `clusteration` application from Dokploy and re-run the success
criteria above.

If there are two Dokploy apps/domains for `app.thiagao.online`, remove the domain
from the stale app and keep it only on the app whose `applicationId/appName` is
`clusteration-app-14hl7s`.
