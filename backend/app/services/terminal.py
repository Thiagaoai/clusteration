import asyncio
import base64
import json
import uuid
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime

import asyncssh
from fastapi import WebSocket
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import SSHStatus, TerminalSession, TerminalSessionStatus, VM, VMStatus


class TerminalConnectError(Exception):
    pass


def as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass
class TerminalProcess:
    conn: asyncssh.SSHClientConnection
    proc: asyncssh.SSHClientProcess

    async def close(self) -> None:
        with suppress(Exception):
            self.proc.terminate()
        with suppress(Exception):
            self.conn.close()
            await self.conn.wait_closed()


def _load_private_key(settings: Settings):
    configured = settings.CONSOLE_SSH_PRIVATE_KEY.strip()
    if configured.startswith("-----BEGIN"):
        raw = configured
    else:
        raw = base64.b64decode(configured).decode("utf-8")
    return asyncssh.import_private_key(raw)


async def open_terminal(ip: str, settings: Settings, cols: int = 120, rows: int = 40) -> TerminalProcess:
    try:
        conn = await asyncio.wait_for(
            asyncssh.connect(
                host=ip,
                port=settings.CONSOLE_SSH_PORT,
                username=settings.CONSOLE_SSH_USER,
                client_keys=[_load_private_key(settings)],
                known_hosts=None,
                login_timeout=15.0,
                keepalive_interval=20,
                keepalive_count_max=3,
            ),
            timeout=15.0,
        )
        proc = await conn.create_process(
            term_type="xterm-256color",
            term_size=(cols, rows),
            encoding=None,
        )
        return TerminalProcess(conn=conn, proc=proc)
    except Exception as exc:
        raise TerminalConnectError(exc.__class__.__name__) from exc


async def check_ssh_ready(db: AsyncSession, settings: Settings, vm: VM) -> bool:
    if not vm.ip_address:
        vm.ssh_status = SSHStatus.failed.value
        await db.commit()
        return False

    loop = asyncio.get_running_loop()
    deadline = loop.time() + 90.0
    while True:
        try:
            term = await open_terminal(vm.ip_address, settings)
            await term.close()
            vm.ssh_status = SSHStatus.ready.value
            await db.commit()
            return True
        except TerminalConnectError:
            if loop.time() >= deadline:
                vm.ssh_status = SSHStatus.failed.value
                await db.commit()
                return False
            await asyncio.sleep(5.0)


async def validate_and_claim_session(db: AsyncSession, session_id: str) -> tuple[TerminalSession, VM] | None:
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        return None

    ts = await db.scalar(select(TerminalSession).where(TerminalSession.id == sid))
    if ts is None or ts.status != TerminalSessionStatus.pending.value:
        return None
    now = datetime.now(UTC)
    if as_aware_utc(ts.expires_at) <= now:
        ts.status = TerminalSessionStatus.expired.value
        await db.commit()
        return None
    vm = await db.get(VM, ts.vm_id)
    if (
        vm is None
        or vm.deleted_at is not None
        or not vm.ip_address
        or vm.status != VMStatus.running.value
        or vm.ssh_status != SSHStatus.ready.value
    ):
        return None
    result = await db.execute(
        update(TerminalSession)
        .where(TerminalSession.id == sid, TerminalSession.status == TerminalSessionStatus.pending.value)
        .values(status=TerminalSessionStatus.connected.value)
    )
    if result.rowcount != 1:
        return None
    await db.commit()
    await db.refresh(ts)
    return ts, vm


async def terminal_websocket(websocket: WebSocket, db: AsyncSession, settings: Settings, session_id: str) -> None:
    claimed = await validate_and_claim_session(db, session_id)
    if claimed is None:
        await websocket.close(code=4401)
        return

    ts, vm = claimed
    await websocket.accept()
    await websocket.send_text(json.dumps({"type": "status", "status": "connecting"}))
    term: TerminalProcess | None = None
    last_input = asyncio.get_running_loop().time()
    close_reason = "session_closed"

    try:
        term = await open_terminal(vm.ip_address or "", settings)
        await websocket.send_text(json.dumps({"type": "status", "status": "connected"}))

        async def ssh_to_ws():
            nonlocal close_reason
            while True:
                data = await term.proc.stdout.read(65536)
                if not data:
                    close_reason = "ssh_error"
                    return
                await websocket.send_bytes(data)

        async def ws_to_ssh():
            nonlocal last_input, close_reason
            while True:
                if asyncio.get_running_loop().time() - last_input > 1800:
                    close_reason = "inactivity_timeout"
                    return
                try:
                    message = await asyncio.wait_for(websocket.receive(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue
                if "bytes" in message and message["bytes"] is not None:
                    last_input = asyncio.get_running_loop().time()
                    term.proc.stdin.write(message["bytes"])
                elif "text" in message and message["text"] is not None:
                    payload = json.loads(message["text"])
                    if payload.get("type") == "resize":
                        last_input = asyncio.get_running_loop().time()
                        term.proc.change_terminal_size(int(payload["cols"]), int(payload["rows"]))
                    elif payload.get("type") == "ping":
                        last_input = asyncio.get_running_loop().time()
                        await websocket.send_text(json.dumps({"type": "pong"}))

        tasks = {asyncio.create_task(ssh_to_ws()), asyncio.create_task(ws_to_ssh())}
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in done:
            task.result()
    except asyncio.TimeoutError:
        close_reason = "inactivity_timeout"
    except Exception:
        close_reason = "ssh_error"
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": "erro ao conectar no terminal"}))
        except Exception:
            pass
    finally:
        if term is not None:
            await term.close()
        ts.status = TerminalSessionStatus.closed.value
        ts.closed_at = datetime.now(UTC)
        await db.commit()
        try:
            await websocket.send_text(json.dumps({"type": "close", "reason": close_reason}))
            await websocket.close(code=1000)
        except Exception:
            pass
