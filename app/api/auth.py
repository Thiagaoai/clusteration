from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.core.auth import require_admin, verify_login
from app.core.config import get_settings
from app.core.errors import AppHTTPException

router = APIRouter(prefix="/api/auth")


class LoginPayload(BaseModel):
    username: str
    password: str


@router.post("/login")
async def login(payload: LoginPayload, request: Request):
    if not verify_login(payload.username, payload.password, get_settings()):
        raise AppHTTPException("INVALID_CREDENTIALS", "credenciais inválidas", 401)
    request.session["authenticated"] = True
    return {"authenticated": True}


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"authenticated": False}


@router.get("/me", dependencies=[Depends(require_admin)])
async def me():
    return {"authenticated": True, "username": get_settings().ADMIN_USERNAME}
