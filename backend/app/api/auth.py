import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.core.auth import require_admin, verify_login
from app.core.config import get_settings
from app.core.errors import AppHTTPException

router = APIRouter(prefix="/api/auth")

# Simple in-process brute-force throttle (single-tenant, single instance).
_LOGIN_FAILS: dict[str, list[float]] = defaultdict(list)
_LOGIN_WINDOW = 300.0  # seconds
_LOGIN_MAX_FAILS = 8


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class LoginPayload(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(payload: LoginPayload, request: Request):
    ip = _client_ip(request)
    now = time.monotonic()
    fails = [t for t in _LOGIN_FAILS[ip] if now - t < _LOGIN_WINDOW]
    _LOGIN_FAILS[ip] = fails
    if len(fails) >= _LOGIN_MAX_FAILS:
        raise AppHTTPException("RATE_LIMITED", "muitas tentativas; aguarde alguns minutos", 429)
    if not verify_login(payload.username, payload.password, get_settings()):
        fails.append(now)
        _LOGIN_FAILS[ip] = fails
        raise AppHTTPException("INVALID_CREDENTIALS", "credenciais inválidas", 401)
    _LOGIN_FAILS.pop(ip, None)
    request.session["authenticated"] = True
    return {"authenticated": True}


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"authenticated": False}


@router.get("/me", dependencies=[Depends(require_admin)])
async def me():
    return {"authenticated": True, "username": get_settings().ADMIN_USERNAME}
