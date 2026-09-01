from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import templates
from ..models import Role
from ..security import authenticate, current_user, hash_password, require_user, verify_password
from ..services.audit import add_audit

router = APIRouter()

PORTALS = {
    "client": {
        "title": "Client Portal",
        "subtitle": "Track your company samples and access released reports.",
        "roles": {Role.CLIENT.value},
    },
    "field": {
        "title": "Field Sampling",
        "subtitle": "Authorized sample collection team access.",
        "roles": {Role.FIELD_SAMPLER.value, Role.CLIENT_SAMPLER.value, Role.CLIENT_OPERATIONS.value},
    },
    "employee": {
        "title": "Employee Sign In",
        "subtitle": "Authorized TSCO laboratory and management personnel only.",
        "roles": {role.value for role in Role if role not in {Role.CLIENT, Role.FIELD_SAMPLER, Role.CLIENT_SAMPLER, Role.CLIENT_OPERATIONS}},
    },
}


def _truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@router.get("/welcome")
def welcome(request: Request, db: Session = Depends(get_db)):
    if current_user(request, db):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("welcome.html", {"request": request})


@router.get("/login")
def login_legacy():
    return RedirectResponse("/welcome", status_code=303)


@router.get("/login/{portal}")
def login_page(portal: str, request: Request, db: Session = Depends(get_db)):
    if current_user(request, db):
        return RedirectResponse("/", status_code=303)
    config = PORTALS.get(portal)
    if not config:
        return RedirectResponse("/welcome", status_code=303)
    demo_accounts = []
    if _truthy("SHOW_DEMO_ACCOUNTS", "false"):
        demo_accounts = {
            "client": [("SEC Client", "client@sec.local")],
            "field": [
                ("TSCO Field Sampler", "fieldman@tsco.local"),
                ("SEC Client Sampler", "clientsampler@sec.local"),
                ("SEC Client Operations", "clientops@sec.local"),
            ],
            "employee": [
                ("Operations Manager", "operations@tsco.local"),
                ("Sampling Supervisor", "supervisor@tsco.local"),
                ("Data Entry", "intake@tsco.local"),
                ("Receiving", "receiving@tsco.local"),
                ("Laboratory Chemist", "chemist@tsco.local"),
                ("Senior Chemist", "senior@tsco.local"),
                ("Quality", "quality@tsco.local"),
                ("Management", "manager@tsco.local"),
                ("Administrator", "admin@tsco.local"),
            ],
        }[portal]
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": "",
            "portal": portal,
            "portal_title": config["title"],
            "portal_subtitle": config["subtitle"],
            "demo_accounts": demo_accounts,
        },
    )


@router.post("/login/{portal}")
def login(
    portal: str,
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    config = PORTALS.get(portal)
    if not config:
        return RedirectResponse("/welcome", status_code=303)
    user = authenticate(db, email, password)
    if not user or user.role not in config["roles"]:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid credentials for this portal",
                "portal": portal,
                "portal_title": config["title"],
                "portal_subtitle": config["subtitle"],
                "demo_accounts": [],
            },
            status_code=401,
        )
    request.session["user_id"] = user.id
    request.session["portal"] = portal
    user.last_login_at = datetime.utcnow()
    add_audit(
        db,
        actor=user,
        request=request,
        action="LOGIN",
        entity_type="User",
        entity_id=user.id,
        summary=f"Signed in through {portal} portal",
    )
    db.commit()
    if user.must_change_password:
        return RedirectResponse("/change-password", status_code=303)
    return RedirectResponse("/", status_code=303)


@router.get("/change-password")
def change_password_page(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    return templates.TemplateResponse("change_password.html", {"request": request, "user": user, "error": "", "ok": ""})


@router.post("/change-password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    error = ""
    if not verify_password(current_password, user.password_hash):
        error = "Current password is incorrect"
    elif len(new_password) < 10:
        error = "New password must be at least 10 characters"
    elif new_password != confirm_password:
        error = "Password confirmation does not match"
    if error:
        return templates.TemplateResponse("change_password.html", {"request": request, "user": user, "error": error, "ok": ""}, status_code=400)
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    add_audit(db, actor=user, request=request, action="PASSWORD_CHANGED", entity_type="User", entity_id=user.id, summary="User changed password")
    db.commit()
    return templates.TemplateResponse("change_password.html", {"request": request, "user": user, "error": "", "ok": "Password updated successfully"})


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if user:
        add_audit(db, actor=user, request=request, action="LOGOUT", entity_type="User", entity_id=user.id, summary="Signed out")
        db.commit()
    request.session.clear()
    return RedirectResponse("/welcome", status_code=303)
