import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.api.internal import router as internal_router
from app.api.routes import router as api_router
from app.core.config import get_settings
from app.core.errors import (
    AppHTTPException,
    RequestIdMiddleware,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.db.session import AsyncSessionLocal, get_db
from app.services.lifecycle import mark_orphaned_running_as_failed, seed_templates
from app.services.terminal import terminal_websocket
from app.ui.routes import router as ui_router
from app.workers.inprocess import requeue_queued_jobs, worker_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as db:
        await seed_templates(db, get_settings())
        await mark_orphaned_running_as_failed(db)
    worker_task = asyncio.create_task(worker_loop())
    await requeue_queued_jobs()
    yield
    worker_task.cancel()


settings = get_settings()
app = FastAPI(title="Proxmox VM Panel", lifespan=lifespan)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=settings.SESSION_MAX_AGE,
    same_site="lax",
    https_only=settings.ENVIRONMENT == "production",
)
app.add_exception_handler(AppHTTPException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(api_router)
app.include_router(internal_router)
app.include_router(ui_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/terminal/ws")
async def terminal_ws(websocket: WebSocket, session_id: str, db: AsyncSession = Depends(get_db)):
    await terminal_websocket(websocket, db, settings, session_id)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    request_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "erro interno", "request_id": request_id}},
        headers={"X-Request-Id": request_id},
    )

