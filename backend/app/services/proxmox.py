import asyncio
import math
import re
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
            detail = sanitize_proxmox_error(last_exc)
            raise ProxmoxAuthError(f"Proxmox recusou {method} {path}: {detail}")
        raise ProxmoxError(sanitize_proxmox_error(last_exc))

    async def get(self, path: str, **kwargs) -> Any:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, data: Any | None = None, **kwargs) -> Any:
        return await self._request("POST", path, data=data, **kwargs)

    async def put(self, path: str, data: Any | None = None, **kwargs) -> Any:
        return await self._request("PUT", path, data=data, **kwargs)

    async def delete(self, path: str, **kwargs) -> Any:
        return await self._request("DELETE", path, **kwargs)

    async def next_id(self) -> int:
        return int(await self.get("/cluster/nextid"))

    async def cluster_resources(self, resource_type: str = "vm") -> list[dict[str, Any]]:
        data = await self.get("/cluster/resources", params={"type": resource_type})
        return data if isinstance(data, list) else []

    async def find_vm_resource(self, vmid: int) -> dict[str, Any] | None:
        for resource in await self.cluster_resources("vm"):
            try:
                if int(resource.get("vmid")) == int(vmid):
                    return resource
            except (TypeError, ValueError):
                continue
        return None

    async def vm_config(self, node: str, vmid: int) -> dict[str, Any]:
        data = await self.get(f"/nodes/{node}/qemu/{vmid}/config")
        return data if isinstance(data, dict) else {}

    async def resolve_template_node(self, preferred_node: str, template_vmid: int) -> str:
        """Find the node that actually owns the template VMID.

        The cluster uses node-local storage, so cloning from a synthetic/default node
        (for example "pve" instead of "pve1") fails even when the token is valid.
        """
        preferred_error = ""
        if preferred_node:
            try:
                config = await self.vm_config(preferred_node, template_vmid)
                if is_template_config(config):
                    return preferred_node
                raise ProxmoxError(
                    f"VMID {template_vmid} existe em {preferred_node}, mas não está marcado como template"
                )
            except ProxmoxError as exc:
                # A failure on the configured node is not fatal on its own: the cluster
                # has no shared storage, so the template can live on another node and
                # the per-node config path may even 403 when the VMID is owned
                # elsewhere. Fall back to the cluster-wide lookup before giving up — a
                # genuinely broken token also fails /cluster/resources below and
                # surfaces there with the same auth error.
                preferred_error = str(exc)

        resource = await self.find_vm_resource(template_vmid)
        if resource is None:
            suffix = f" node configurado respondeu: {preferred_error}" if preferred_error else ""
            raise ProxmoxError(f"template VMID {template_vmid} não encontrado no cluster.{suffix}")
        if not is_template_resource(resource):
            raise ProxmoxError(f"VMID {template_vmid} encontrado, mas não está marcado como template")
        node = str(resource.get("node") or "").strip()
        if not node:
            raise ProxmoxError(f"template VMID {template_vmid} encontrado sem node no Proxmox")
        return node

    async def resolve_vm_node(self, preferred_node: str, vmid: int) -> str:
        if preferred_node:
            try:
                await self.get(f"/nodes/{preferred_node}/qemu/{vmid}/status/current")
                return preferred_node
            except ProxmoxError:
                # The VM may live on another node (no shared storage), where the
                # configured-node path can 403/fail. Resolve via the cluster-wide
                # lookup; a broken token re-surfaces on /cluster/resources below.
                pass
        resource = await self.find_vm_resource(vmid)
        if resource is None:
            raise ProxmoxError(f"VMID {vmid} não encontrado no cluster")
        node = str(resource.get("node") or "").strip()
        if not node:
            raise ProxmoxError(f"VMID {vmid} encontrado sem node no Proxmox")
        return node

    async def vm_disk_size_gb(self, node: str, vmid: int, disk: str = "scsi0") -> int | None:
        config = await self.vm_config(node, vmid)
        return parse_disk_size_gb(str(config.get(disk) or ""))

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
                raise ProxmoxTimeoutError(f"guest-agent não retornou IP em {timeout:.0f}s")
            await asyncio.sleep(interval)

    async def agent_exec(self, node: str, vmid: int, script: str, timeout: float = 60.0) -> str:
        """Run a shell script inside the guest via the qemu-guest-agent and return its stdout."""
        started = await self.post(
            f"/nodes/{node}/qemu/{vmid}/agent/exec",
            data={"command": "bash", "extra-args": ["-lc", script], "capture-output": "1"},
        )
        pid = started.get("pid") if isinstance(started, dict) else None
        if pid is None:
            return ""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            status = await self.get(
                f"/nodes/{node}/qemu/{vmid}/agent/exec-status", params={"pid": pid}
            )
            if isinstance(status, dict) and status.get("exited"):
                return str(status.get("out-data") or "")
            if loop.time() >= deadline:
                return ""
            await asyncio.sleep(1.5)

    async def reset_machine_id(self, node: str, vmid: int) -> None:
        """Give the guest a fresh machine-id so it requests a unique DHCP lease.

        Cloud-init templates ship with a baked machine-id; since the DHCP server keys
        leases on the DUID (derived from machine-id), every clone otherwise collides on
        the same IP, which breaks console SSH. Resetting it makes each VM get its own IP.
        """
        script = (
            "rm -f /etc/machine-id /var/lib/dbus/machine-id && "
            "systemd-machine-id-setup >/dev/null 2>&1 && "
            "ln -sf /etc/machine-id /var/lib/dbus/machine-id && "
            "echo reset-ok"
        )
        # The guest-exec channel lags the network agent by ~20-40s right after boot
        # (cloud-init / systemd still settling), so the very first attempt during a
        # create often fails. Poll until the reset actually lands.
        last_exc: Exception | None = None
        for _ in range(15):
            try:
                out = await self.agent_exec(node, vmid, script)
                if "reset-ok" in out:
                    return
            except ProxmoxError as exc:
                last_exc = exc
            await asyncio.sleep(6.0)
        if last_exc is not None:
            raise last_exc
        raise ProxmoxError("reset de machine-id não confirmou (guest-exec indisponível)")


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


def is_template_resource(resource: dict[str, Any]) -> bool:
    return str(resource.get("template") or "").lower() in {"1", "true", "yes"}


def is_template_config(config: dict[str, Any]) -> bool:
    return str(config.get("template") or "").lower() in {"1", "true", "yes"}


def parse_disk_size_gb(value: str) -> int | None:
    match = re.search(r"(?:^|,)size=(\d+(?:\.\d+)?)([KMGT])(?:i?B)?(?:,|$)", value, re.IGNORECASE)
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2).upper()
    factor = {"K": 1 / (1024 * 1024), "M": 1 / 1024, "G": 1, "T": 1024}[unit]
    return max(1, math.ceil(amount * factor))


def sanitize_proxmox_error(exc: Exception | None) -> str:
    if exc is None:
        return "erro ao chamar Proxmox"
    if isinstance(exc, httpx.ConnectError):
        return "não foi possível conectar ao Proxmox; verifique PROXMOX_HOST, rede e firewall"
    if isinstance(exc, httpx.TimeoutException):
        return "Proxmox não respondeu dentro do tempo limite; verifique API, rede e carga do node"
    if isinstance(exc, httpx.HTTPStatusError):
        detail = ""
        try:
            payload = exc.response.json()
            detail = str(payload.get("message") or payload.get("errors") or "")
            if payload.get("errors") and payload.get("message"):
                detail = f"{payload.get('message')}: {payload.get('errors')}"
        except Exception:
            detail = exc.response.text.strip()
        detail = detail.replace("\n", " ").strip()
        if detail:
            return f"Proxmox respondeu HTTP {exc.response.status_code}: {detail[:300]}"
        return f"Proxmox respondeu HTTP {exc.response.status_code}"
    return exc.__class__.__name__
