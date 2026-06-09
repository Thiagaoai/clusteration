import asyncio
import os
import time
from collections.abc import AsyncIterator

import httpx
import websockets
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, StreamingResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket

API_INTERNAL_URL = os.getenv("API_INTERNAL_URL", "http://127.0.0.1:8000")
PROXY_SECRET = os.getenv("EXPOSURE_PROXY_SECRET", "")
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
_cache: dict[str, tuple[float, str | None]] = {}


async def resolve(host: str) -> str | None:
    now = time.monotonic()
    cached = _cache.get(host)
    if cached and cached[0] > now:
        return cached[1]
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            f"{API_INTERNAL_URL}/internal/exposure-upstream",
            params={"host": host},
            headers={"X-Proxy-Secret": PROXY_SECRET},
        )
    data = response.json() if response.status_code == 200 else []
    dial = data[0]["dial"] if data else None
    _cache[host] = (now + 5.0, dial)
    return dial


async def proxy_http(request: Request):
    host = request.headers.get("host", "")
    dial = await resolve(host)
    if not dial:
        return PlainTextResponse("not found", status_code=404)

    path = request.url.path
    query = f"?{request.url.query}" if request.url.query else ""
    upstream = f"http://{dial}{path}{query}"
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP and k.lower() != "host"
    }
    headers["x-forwarded-proto"] = "https"
    headers["x-forwarded-host"] = host
    headers["x-forwarded-for"] = request.client.host if request.client else ""

    client = httpx.AsyncClient(timeout=None)
    upstream_response = await client.stream(
        request.method,
        upstream,
        headers=headers,
        content=request.stream(),
    ).__aenter__()

    async def body() -> AsyncIterator[bytes]:
        try:
            async for chunk in upstream_response.aiter_bytes():
                yield chunk
        finally:
            await upstream_response.aclose()
            await client.aclose()

    response_headers = {
        k: v for k, v in upstream_response.headers.items() if k.lower() not in HOP_BY_HOP
    }
    return StreamingResponse(body(), status_code=upstream_response.status_code, headers=response_headers)


async def proxy_ws(websocket: WebSocket):
    host = websocket.headers.get("host", "")
    dial = await resolve(host)
    if not dial:
        await websocket.close(code=1008)
        return
    path = websocket.url.path
    query = f"?{websocket.url.query}" if websocket.url.query else ""
    await websocket.accept()
    async with websockets.connect(f"ws://{dial}{path}{query}") as upstream:
        async def browser_to_upstream():
            while True:
                msg = await websocket.receive()
                if msg.get("bytes") is not None:
                    await upstream.send(msg["bytes"])
                elif msg.get("text") is not None:
                    await upstream.send(msg["text"])

        async def upstream_to_browser():
            async for msg in upstream:
                if isinstance(msg, bytes):
                    await websocket.send_bytes(msg)
                else:
                    await websocket.send_text(msg)

        tasks = {asyncio.create_task(browser_to_upstream()), asyncio.create_task(upstream_to_browser())}
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in done:
            task.result()


routes = [
    WebSocketRoute("/{path:path}", proxy_ws),
    Route("/{path:path}", proxy_http, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]),
]
app = Starlette(routes=routes)

