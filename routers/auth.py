import uuid
from typing import Optional

from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, utc_now
from auth_helper import (
    verify_password,
    hash_password,
    create_session_token,
    validate_password_strength
)
from dependencies import render, log_audit_event, get_current_user

router = APIRouter(tags=["Authentication"])

@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user)
):
    if user:
        return RedirectResponse(url=next or "/dashboard", status_code=status.HTTP_302_FOUND)
    return render(request, "login.html", {"error": None, "next": next})

@router.post("/login", response_class=HTMLResponse)
async def handle_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    email_clean = email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email_clean).first()

    if user and verify_password(password, user.password_hash):
        if user.status != "Active":
            log_audit_event(
                db, "LOGIN_BLOCKED_DEACTIVATED",
                f"Deactivated officer login attempt: {email_clean}",
                user_id=user.id, ip_address=client_ip
            )
            return render(request, "login.html", {
                "error": "Official account is deactivated. Contact Department Administrator.",
                "email": email,
                "next": next
            })
        
        user.last_login = utc_now()
        db.commit()

        log_audit_event(
            db, "LOGIN_SUCCESS",
            f"Officer sign-in [{user.role.upper()}]: {user.full_name} ({email_clean})",
            user_id=user.id, ip_address=client_ip
        )

        target_url = next if next and next.startswith("/") else "/dashboard"
        response = RedirectResponse(url=target_url, status_code=status.HTTP_302_FOUND)
        token = create_session_token(user.id)
        response.set_cookie(key="session_token", value=token, httponly=True, samesite="lax", max_age=86400 * 7)
        return response

    log_audit_event(
        db, "LOGIN_FAILED",
        f"Invalid credentials submitted for email: {email_clean}",
        ip_address=client_ip
    )
    return render(request, "login.html", {
        "error": "Invalid official credentials. Please check your email and password.",
        "email": email,
        "next": next
    })

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return render(request, "register.html", {"error": None, "form": {}})

@router.post("/register", response_class=HTMLResponse)
async def handle_register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    employee_id: Optional[str] = Form(None),
    department: Optional[str] = Form("Legal Metrology Enforcement"),
    role: str = Form("inspector"),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    form_data = {
        "full_name": full_name,
        "email": email,
        "employee_id": employee_id,
        "department": department,
        "role": role
    }

    # Strict Security: Admin role cannot be created via public registration!
    if role not in ["inspector", "officer"]:
        log_audit_event(
            db, "UNAUTHORIZED_ADMIN_REGISTRATION_ATTEMPT",
            f"Attempt to register unauthorized role '{role}' from IP {client_ip}",
            ip_address=client_ip
        )
        return render(request, "register.html", {
            "error": "Security Restriction: Administrative roles cannot be registered through the public portal.",
            "form": form_data
        })

    if not full_name.strip():
        return render(request, "register.html", {"error": "Full officer name is required.", "form": form_data})

    email_clean = email.strip().lower()
    if "@" not in email_clean or "." not in email_clean:
        return render(request, "register.html", {"error": "Please provide a valid official email address.", "form": form_data})

    is_valid_pwd, pwd_err = validate_password_strength(password)
    if not is_valid_pwd:
        return render(request, "register.html", {"error": f"Security Requirement: {pwd_err}", "form": form_data})

    if password != confirm_password:
        return render(request, "register.html", {"error": "Passwords do not match.", "form": form_data})

    existing_user = db.query(User).filter(func.lower(User.email) == email_clean).first()
    if existing_user:
        return render(request, "register.html", {"error": "An officer profile with this email already exists. Please sign in.", "form": form_data})

    emp_id = employee_id.strip() if employee_id and employee_id.strip() else f"DOCA-{uuid.uuid4().hex[:6].upper()}"
    existing_emp = db.query(User).filter(User.employee_id == emp_id).first()
    if existing_emp:
        emp_id = f"DOCA-{uuid.uuid4().hex[:6].upper()}"

    pwd_hash = hash_password(password)
    designation_title = "Legal Metrology Inspector" if role == "inspector" else "Assistant Controller of Legal Metrology"

    new_user = User(
        employee_id=emp_id,
        full_name=full_name.strip(),
        email=email_clean,
        password_hash=pwd_hash,
        role=role,
        department=department.strip() if department else "Legal Metrology Enforcement",
        designation=designation_title,
        office_region="Zone 1 - Central Headquarters",
        status="Active",
        last_login=utc_now()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit_event(
        db, "OFFICER_REGISTERED",
        f"New {role.upper()} profile created: {new_user.full_name} ({email_clean}) - Badge: {emp_id}",
        user_id=new_user.id, ip_address=client_ip
    )

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    token = create_session_token(new_user.id)
    response.set_cookie(key="session_token", value=token, httponly=True, samesite="lax", max_age=86400 * 7)
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="session_token")
    response.delete_cookie(key="user_id")
    return response
