import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import serialize_vm
from app.core.auth import require_admin, verify_login
from app.core.config import VM_SIZES, get_settings
from app.core.readiness import missing_runtime_settings
from app.db.session import get_db
from app.models import Template, VM, VMStatus

templates = Jinja2Templates(directory="app/templates")
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if verify_login(username, password, get_settings()):
        request.session["authenticated"] = True
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": "Credenciais inválidas"}, status_code=401)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="dashboard.html", context=await dashboard_context(db))


@router.get("/partials/vm-table", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def vm_table(request: Request, db: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse(request=request, name="partials/vm_table.html", context=await dashboard_context(db))


@router.get("/vms/new", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def new_vm(request: Request, db: AsyncSession = Depends(get_db)):
    tpls = (await db.scalars(select(Template).order_by(Template.os))).all()
    return templates.TemplateResponse(
        request=request,
        name="new_vm.html",
        context={
            "templates": tpls,
            "sizes": VM_SIZES,
            "disk_choices": get_settings().VM_DISK_CHOICES,
            "missing_runtime": missing_runtime_settings(get_settings()),
        },
    )


@router.get("/admin/security", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def security_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="security.html",
        context={"error": None, "success": None, "admin_username": get_settings().ADMIN_USERNAME},
    )


@router.post("/admin/security/password", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def update_admin_password(
    request: Request,
    current_password: str = Form(...),
    admin_username: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    settings = get_settings()
    username = admin_username.strip()
    if not verify_login(settings.ADMIN_USERNAME, current_password, settings):
        return templates.TemplateResponse(
            request=request,
            name="security.html",
            context={"error": "Senha atual inválida.", "success": None, "admin_username": settings.ADMIN_USERNAME},
            status_code=400,
        )
    if not username:
        return templates.TemplateResponse(
            request=request,
            name="security.html",
            context={"error": "Usuário admin não pode ficar vazio.", "success": None, "admin_username": settings.ADMIN_USERNAME},
            status_code=400,
        )
    if len(new_password) < 8:
        return templates.TemplateResponse(
            request=request,
            name="security.html",
            context={"error": "A nova senha precisa ter pelo menos 8 caracteres.", "success": None, "admin_username": settings.ADMIN_USERNAME},
            status_code=400,
        )
    if new_password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="security.html",
            context={"error": "A confirmação da nova senha não confere.", "success": None, "admin_username": settings.ADMIN_USERNAME},
            status_code=400,
        )

    update_env_values(
        {
            "ADMIN_USERNAME": username,
            "ADMIN_PASSWORD_HASH": pwd_context.hash(new_password),
        }
    )
    get_settings.cache_clear()
    request.session["authenticated"] = True
    return templates.TemplateResponse(
        request=request,
        name="security.html",
        context={"error": None, "success": "Credenciais administrativas atualizadas.", "admin_username": username},
    )


@router.get("/vms/{vm_id}", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def vm_detail(request: Request, vm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    vm = await db.get(VM, vm_id)
    if vm is None or vm.deleted_at is not None:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request=request, name="vm_detail.html", context={"vm": serialize_vm(vm)})


@router.get("/vms/{vm_id}/terminal", response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def terminal_page(request: Request, vm_id: uuid.UUID, session: str):
    return templates.TemplateResponse(
        request=request, name="terminal.html", context={"vm_id": str(vm_id), "session_id": session}
    )


async def dashboard_context(db: AsyncSession) -> dict:
    rows = (await db.scalars(select(VM).where(VM.deleted_at.is_(None)).order_by(VM.created_at.desc()))).all()
    vms = [serialize_vm(vm) for vm in rows]
    transient = {VMStatus.creating.value, VMStatus.provisioning.value, VMStatus.starting.value, VMStatus.stopping.value, VMStatus.rebooting.value, VMStatus.deleting.value}
    return {"vms": vms, "has_transient": any(vm.status in transient for vm in vms)}


def update_env_values(updates: dict[str, str]) -> None:
    env_path = Path(".env")
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    for key, value in updates.items():
        for index, line in enumerate(lines):
            if line.startswith(key + "="):
                lines[index] = f"{key}={value}"
                break
        else:
            lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n")

