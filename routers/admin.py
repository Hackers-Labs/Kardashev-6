import uuid
from typing import Optional

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import User, AuditLog, utc_now
from auth_helper import hash_password, validate_password_strength
from dependencies import (
    render,
    log_audit_event,
    get_current_user,
    require_admin
)

router = APIRouter(tags=["Administration & Governance"])

@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Enforcement Officer Directory & Account Administration."""
    users = db.query(User).order_by(User.id.asc()).all()
    return render(request, "admin_users.html", {
        "current_user": user,
        "page_title": "Enforcement Officer Directory & Administration",
        "active_nav": "admin_users",
        "users": users
    })

@router.post("/api/admin/users/{id}/toggle-status")
async def admin_toggle_user_status(
    id: int,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Activates or deactivates an officer's access credentials."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    target = db.query(User).filter(User.id == id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Officer record not found.")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Security Restriction: System Administrator cannot deactivate their own account.")

    new_status = "Inactive" if target.status == "Active" else "Active"
    target.status = new_status
    db.commit()

    log_audit_event(
        db, "USER_STATUS_TOGGLED",
        f"Officer account {target.full_name} ({target.email}) status changed to '{new_status}' by Admin {user.full_name}",
        user_id=user.id, ip_address=client_ip
    )
    return {"success": True, "new_status": new_status, "user_id": target.id}

@router.post("/api/admin/users/{id}/change-role")
async def admin_change_user_role(
    id: int,
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Updates an officer's role between inspector and officer."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    target = db.query(User).filter(User.id == id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Officer record not found.")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Security Restriction: System Administrator role cannot be altered.")

    payload = await request.json()
    new_role = payload.get("role")
    if new_role not in ["inspector", "officer"]:
        raise HTTPException(status_code=400, detail="Invalid role specified. Only inspector or officer allowed.")

    target.role = new_role
    if new_role == "officer":
        target.designation = "Assistant Controller of Legal Metrology"
    else:
        target.designation = "Legal Metrology Inspector"
    db.commit()

    log_audit_event(
        db, "USER_ROLE_CHANGED",
        f"Officer {target.full_name} ({target.email}) role transitioned to {new_role.upper()} by Admin {user.full_name}",
        user_id=user.id, ip_address=client_ip
    )
    return {"success": True, "new_role": new_role, "new_designation": target.designation}

@router.post("/api/admin/users/create")
async def admin_create_user(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    employee_id: Optional[str] = Form(None),
    role: str = Form("inspector"),
    department: Optional[str] = Form("Legal Metrology Enforcement"),
    designation: Optional[str] = Form(None),
    password: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Directly onboards an enforcement officer through the administrative directory."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    email_clean = email.strip().lower()

    if role not in ["inspector", "officer"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be inspector or officer.")

    is_valid_pwd, pwd_err = validate_password_strength(password)
    if not is_valid_pwd:
        raise HTTPException(status_code=400, detail=f"Password does not meet security requirements: {pwd_err}")

    existing = db.query(User).filter(func.lower(User.email) == email_clean).first()
    if existing:
        raise HTTPException(status_code=400, detail="An officer with this email already exists.")

    emp_id = employee_id.strip() if employee_id and employee_id.strip() else f"DOCA-{uuid.uuid4().hex[:6].upper()}"
    desig = designation.strip() if designation and designation.strip() else (
        "Assistant Controller of Legal Metrology" if role == "officer" else "Legal Metrology Inspector"
    )

    new_officer = User(
        employee_id=emp_id,
        full_name=full_name.strip(),
        email=email_clean,
        password_hash=hash_password(password),
        role=role,
        department=department.strip() if department else "Legal Metrology Enforcement",
        designation=desig,
        office_region="Zone 1 - Headquarters",
        status="Active",
        created_at=utc_now()
    )
    db.add(new_officer)
    db.commit()
    db.refresh(new_officer)

    log_audit_event(
        db, "ADMIN_OFFICER_CREATED",
        f"New {role.upper()} profile provisioned by Admin: {new_officer.full_name} ({email_clean}) - Badge: {emp_id}",
        user_id=user.id, ip_address=client_ip
    )
    return RedirectResponse(url="/admin/users?success=Officer+provisioned+successfully", status_code=status.HTTP_302_FOUND)

@router.get("/admin/audit-logs", response_class=HTMLResponse)
async def admin_audit_logs_page(
    request: Request,
    action_filter: Optional[str] = None,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Security & Statutory Audit Trail compliant with IT Act 2000 Section 65B."""
    query = db.query(AuditLog)
    if action_filter and action_filter.strip():
        query = query.filter(AuditLog.action == action_filter.strip())
    logs = query.order_by(AuditLog.id.desc()).limit(250).all()
    distinct_actions = [a[0] for a in db.query(AuditLog.action).distinct().all()]

    return render(request, "admin_audit_logs.html", {
        "current_user": user,
        "page_title": "Security & Enforcement Audit Log (IT Act Sec 65B)",
        "active_nav": "admin_audit_logs",
        "logs": logs,
        "actions": distinct_actions,
        "selected_action": action_filter or ""
    })

@router.get("/admin/rules", response_class=HTMLResponse)
async def statutory_rules_reference_page(
    request: Request,
    user: Optional[User] = Depends(get_current_user)
):
    """Statutory Legal Metrology (Packaged Commodities) Rules 2011 Reference Manual."""
    if not user:
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=status.HTTP_302_FOUND)

    return render(request, "admin_rules.html", {
        "current_user": user,
        "page_title": "Statutory Rules & Penalties Reference Manual",
        "active_nav": "admin_rules"
    })
