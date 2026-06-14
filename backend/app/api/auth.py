import secrets
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import pwd, require_admin
from app.core.config import get_settings
from app.core.errors import AppHTTPException
from app.db.session import get_db
from app.models import PasswordReset
from app.services.audit import record_audit
from app.services.credentials import set_admin_password, verify_admin
from app.services.email import email_enabled, send_email

router = APIRouter(prefix="/api/auth")

# Simple in-process throttles (single-tenant, single instance).
_LOGIN_FAILS: dict[str, list[float]] = defaultdict(list)
_RESET_REQUESTS: dict[str, list[float]] = defaultdict(list)
_RESET_ATTEMPTS: dict[str, list[float]] = defaultdict(list)
_LOGIN_WINDOW = 300.0
_LOGIN_MAX_FAILS = 8


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _throttle(bucket: dict[str, list[float]], ip: str, window: float, max_hits: int) -> bool:
    now = time.monotonic()
    hits = [t for t in bucket[ip] if now - t < window]
    if len(hits) >= max_hits:
        bucket[ip] = hits
        return False
    hits.append(now)
    bucket[ip] = hits
    return True


def _mask_email(addr: str) -> str:
    try:
        user, domain = addr.split("@", 1)
        head = user[0] if user else "*"
        return f"{head}***@{domain}"
    except Exception:
        return "seu email"


class LoginPayload(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(payload: LoginPayload, request: Request, db: AsyncSession = Depends(get_db)):
    ip = _client_ip(request)
    now = time.monotonic()
    fails = [t for t in _LOGIN_FAILS[ip] if now - t < _LOGIN_WINDOW]
    _LOGIN_FAILS[ip] = fails
    if len(fails) >= _LOGIN_MAX_FAILS:
        await record_audit(db, action="auth.login_blocked", request=request, actor=payload.username, commit=True)
        raise AppHTTPException("RATE_LIMITED", "muitas tentativas; aguarde alguns minutos", 429)
    if not await verify_admin(db, payload.username, payload.password, get_settings()):
        fails.append(now)
        _LOGIN_FAILS[ip] = fails
        await record_audit(db, action="auth.login_failed", request=request, actor=payload.username, commit=True)
        raise AppHTTPException("INVALID_CREDENTIALS", "credenciais inválidas", 401)
    _LOGIN_FAILS.pop(ip, None)
    request.session["authenticated"] = True
    await record_audit(db, action="auth.login", request=request, actor=payload.username, commit=True)
    return {"authenticated": True}


@router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    await record_audit(db, action="auth.logout", request=request, actor=get_settings().ADMIN_USERNAME, commit=True)
    request.session.clear()
    return {"authenticated": False}


@router.get("/me", dependencies=[Depends(require_admin)])
async def me():
    settings = get_settings()
    return {"authenticated": True, "username": settings.ADMIN_USERNAME, "reset_email": email_enabled(settings)}


@router.post("/forgot")
async def forgot(request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    ip = _client_ip(request)
    if not _throttle(_RESET_REQUESTS, ip, 600.0, 3):
        raise AppHTTPException("RATE_LIMITED", "muitas solicitações; aguarde alguns minutos", 429)
    to = settings.RESET_EMAIL_TO or settings.SMTP_USER
    if not email_enabled(settings) or not to:
        raise AppHTTPException("EMAIL_NOT_CONFIGURED", "redefinição por email ainda não está configurada", 503)
    uname = settings.ADMIN_USERNAME
    code = f"{secrets.randbelow(1000000):06d}"
    # invalidate any previous unused codes
    olds = (
        await db.scalars(
            select(PasswordReset).where(PasswordReset.username == uname, PasswordReset.used_at.is_(None))
        )
    ).all()
    for old in olds:
        old.used_at = datetime.now(UTC)
    db.add(
        PasswordReset(
            username=uname,
            code_hash=pwd.hash(code),
            expires_at=datetime.now(UTC) + timedelta(minutes=settings.RESET_CODE_TTL_MINUTES),
        )
    )
    await db.commit()
    body = (
        "Olá,\n\n"
        "Você (ou alguém) pediu para redefinir a senha do Thiagao Ai Cluster.\n\n"
        f"Seu código é:  {code}\n\n"
        f"Ele vale por {settings.RESET_CODE_TTL_MINUTES} minutos e só pode ser usado uma vez.\n"
        "Se não foi você, ignore este email — sua senha continua a mesma.\n"
    )
    try:
        await send_email(settings, to, "Código de redefinição de senha — Thiagao Ai Cluster", body)
    except Exception:
        raise AppHTTPException("EMAIL_SEND_FAILED", "não foi possível enviar o email; verifique a configuração SMTP", 502)
    await record_audit(db, action="auth.reset_requested", request=request, actor=uname, commit=True)
    return {"sent": True, "to": _mask_email(to)}


class ResetPayload(BaseModel):
    code: str
    new_password: str


@router.post("/reset")
async def reset(payload: ResetPayload, request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    ip = _client_ip(request)
    if not _throttle(_RESET_ATTEMPTS, ip, 600.0, 10):
        raise AppHTTPException("RATE_LIMITED", "muitas tentativas; aguarde alguns minutos", 429)
    if len((payload.new_password or "").strip()) < 8:
        raise AppHTTPException("WEAK_PASSWORD", "a nova senha precisa ter ao menos 8 caracteres", 400)
    uname = settings.ADMIN_USERNAME
    now = datetime.now(UTC)
    entry = await db.scalar(
        select(PasswordReset)
        .where(PasswordReset.username == uname, PasswordReset.used_at.is_(None), PasswordReset.expires_at > now)
        .order_by(PasswordReset.created_at.desc())
    )
    if entry is None:
        raise AppHTTPException("INVALID_CODE", "código inválido ou expirado", 400)
    entry.attempts += 1
    if entry.attempts > 6:
        entry.used_at = now
        await db.commit()
        raise AppHTTPException("INVALID_CODE", "código inválido ou expirado", 400)
    try:
        valid = pwd.verify(payload.code.strip(), entry.code_hash)
    except Exception:
        valid = False
    if not valid:
        await db.commit()
        await record_audit(db, action="auth.reset_failed", request=request, actor=uname, commit=True)
        raise AppHTTPException("INVALID_CODE", "código inválido ou expirado", 400)
    entry.used_at = now
    await set_admin_password(db, settings, payload.new_password)
    await record_audit(db, action="auth.password_reset", request=request, actor=uname, commit=True)
    return {"ok": True}


class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password", dependencies=[Depends(require_admin)])
async def change_password(payload: ChangePasswordPayload, request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    if not await verify_admin(db, settings.ADMIN_USERNAME, payload.current_password, settings):
        raise AppHTTPException("INVALID_CREDENTIALS", "senha atual incorreta", 401)
    if len((payload.new_password or "").strip()) < 8:
        raise AppHTTPException("WEAK_PASSWORD", "a nova senha precisa ter ao menos 8 caracteres", 400)
    await set_admin_password(db, settings, payload.new_password)
    await record_audit(db, action="auth.password_changed", request=request, actor=settings.ADMIN_USERNAME, commit=True)
    return {"ok": True}
