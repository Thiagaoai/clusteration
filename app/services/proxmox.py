import asyncio
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import Settings


class ProxmoxError(Exception):
    pass


class ProxmoxAuthError(ProxmoxError):
    pass


class ProxmoxTaskError(ProxmoxError):
    pass


class ProxmoxTimeoutError(ProxmoxError):
    pass


class ProxmoxClient:
    RETRY_STATUSES = {429, 500, 502, 503, 504}

    def __init__(self, settings: Settings):
        token = f"PVEAPIToken={settings.PROXMOX_TOKEN_ID}={settings.PROXMOX_TOKEN_SECRET}"
        self._client = httpx.AsyncClient(
            base_url=f"{settings.PROXMOX_HOST.rstrip('/')}/api2/json",
            headers={"Authorization": token},
            verify=False,
            timeout=30.0,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        last_exc: Exception | None = None
        for attempt in range(4):
            try:
                response = await self._client.request(method, path, **kwargs)
                if response.status_code in self.RETRY_STATUSES:
                    raise httpx.HTTPStatusError("transient proxmox error", request=response.request, response=response)
                response.raise_for_status()
                payload = response.json()
                return payload.get("data")
            except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                last_exc = exc
                status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                if attempt == 3 or (status is not None and status not in self.RETRY_STATUSES):
                    break
                await asyncio.sleep(min(0.5 * (2**attempt), 8.0))
        if isinstance(last_exc, httpx.HTTPStatusError) and last_exc.response.status_code in (401, 403):
            raise ProxmoxAuthError("Proxmox recusou o token/API permissions")
        raise ProxmoxError(sanitize_proxmox_error(last_exc))

    async def get(self, path: str, **kwargs) -> Any:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, data: dict[str, Any] | None = None, **kwargs) -> Any:
        return await self._request("POST", path, data=data, **kwargs)

    async def put(self, path: str, data: dict[str, Any] | None = None, **kwargs) -> Any:
        return await self._request("PUT", path, data=data, **kwargs)

    async def delete(self, path: str, **kwargs) -> Any:
        return await self._request("DELETE", path, **kwargs)

    async def next_id(self) -> int:
        return int(await self.get("/cluster/nextid"))

    async def wait_for_task(self, node: str, upid: str, timeout: float = 600.0, interval: float = 3.0) -> str:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            status = await self.get(f"/nodes/{node}/tasks/{quote(upid, safe='')}/status")
            if status.get("status") == "stopped":
                exit_status = str(status.get("exitstatus") or "")
                if exit_status and exit_status != "OK":
                    raise ProxmoxTaskError(exit_status)
                return exit_status or "OK"
            if loop.time() >= deadline:
                raise ProxmoxTimeoutError(f"task não terminou em {timeout:.0f}s")
            await asyncio.sleep(interval)

    async def wait_for_ip(self, node: str, vmid: int, timeout: float = 180.0, interval: float = 3.0) -> str:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            try:
                data = await self.get(f"/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces")
                ip = parse_first_ipv4(data)
                if ip:
                    return ip
            except ProxmoxError:
                pass
            if loop.time() >= deadline:
                raise ProxmoxTimeoutError("guest-agent não retornou IP em 180s")
            await asyncio.sleep(interval)


def parse_first_ipv4(data: Any) -> str | None:
    interfaces = data.get("result") if isinstance(data, dict) else data
    if not isinstance(interfaces, list):
        return None
    for iface in interfaces:
        if not isinstance(iface, dict):
            continue
        name = str(iface.get("name", "")).lower()
        if name in ("lo", "loopback") or name.startswith("lo"):
            continue
        for addr in iface.get("ip-addresses", []) or []:
            if not isinstance(addr, dict):
                continue
            if addr.get("ip-address-type") != "ipv4":
                continue
            ip = str(addr.get("ip-address", "")).strip()
            if ip and not ip.startswith("127."):
                return ip
    return None


def sanitize_proxmox_error(exc: Exception | None) -> str:
    if exc is None:
        return "erro ao chamar Proxmox"
    if isinstance(exc, httpx.HTTPStatusError):
        detail = ""
        try:
            payload = exc.response.json()
            detail = str(payload.get("message") or payload.get("errors") or "")
        except Exception:
            detail = exc.response.text.strip()
        detail = detail.replace("\n", " ").strip()
        if detail:
            return f"Proxmox respondeu HTTP {exc.response.status_code}: {detail[:300]}"
        return f"Proxmox respondeu HTTP {exc.response.status_code}"
    return exc.__class__.__name__

