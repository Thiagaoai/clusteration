import uuid
from dataclasses import dataclass

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass(frozen=True)
class AppError:
    code: str
    message: str
    status_code: int = 400


class AppHTTPException(HTTPException):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=message)
        self.code = code


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


def error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": request_id}},
        headers={"X-Request-Id": request_id},
    )


async def app_exception_handler(request: Request, exc: AppHTTPException) -> JSONResponse:
    return error_response(request, exc.status_code, exc.code, str(exc.detail))


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = "UNAUTHORIZED" if exc.status_code == 401 else "INTERNAL_ERROR"
    return error_response(request, exc.status_code, code, str(exc.detail))


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(request, 400, "VALIDATION_ERROR", "requisição inválida")

