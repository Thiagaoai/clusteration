import hmac

from fastapi import HTTPException, Request, status
from passlib.context import CryptContext

from app.core.config import Settings

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def require_admin(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")


def verify_login(username: str, password: str, settings: Settings) -> bool:
    if username != settings.ADMIN_USERNAME:
        return False
    if settings.ADMIN_PASSWORD:
        return hmac.compare_digest(password, settings.ADMIN_PASSWORD)
    if settings.ADMIN_PASSWORD_HASH:
        return pwd.verify(password, settings.ADMIN_PASSWORD_HASH)
    return False

