import os
from pathlib import Path
from typing import Optional

from fastapi import Request, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import SessionLocal, get_db
from models import User, AuditLog, utc_now
from auth_helper import hash_password, verify_session_token

# Base and Directory Paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = STATIC_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
(UPLOADS_DIR / "annotated").mkdir(parents=True, exist_ok=True)
(UPLOADS_DIR / "reports").mkdir(parents=True, exist_ok=True)

# Jinja2 Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def render(request: Request, name: str, context: dict = None, status_code: int = 200):
    """Helper to render Jinja2 templates cleanly with context and status code."""
    ctx = context or {}
    return templates.TemplateResponse(request=request, name=name, context=ctx, status_code=status_code)

def init_system_admin():
    """Ensures pre-defined Department System Administrator exists in the database."""
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.role == "admin").first()
        if not admin_user:
            admin_user = User(
                employee_id="DOCA-ADMIN-01",
                full_name="Chief System Administrator",
                email="admin@doca.gov.in",
                password_hash=hash_password("Admin@DoCA2026!"),
                role="admin",
                department="Legal Metrology IT & Surveillance Directorate",
                designation="Chief Systems Director & Administrator",
                office_region="National Headquarters - New Delhi",
                phone="+91 11 2338 1234",
                status="Active",
                created_at=utc_now()
            )
            db.add(admin_user)
            db.commit()
            print("[SECURITY] Pre-defined Department Administrator seeded: admin@doca.gov.in")
        elif not admin_user.password_hash.startswith("pbkdf2:"):
            admin_user.password_hash = hash_password("Admin@DoCA2026!")
            db.commit()
            print("[SECURITY] Department Administrator password hash upgraded to PBKDF2.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to seed system administrator: {e}")
    finally:
        db.close()

def log_audit_event(db: Session, action: str, details: str, user_id: Optional[int] = None, ip_address: Optional[str] = None):
    """Logs security and compliance events into the immutable AuditLog table (IT Act 2000 Section 65B)."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address or "127.0.0.1",
            created_at=utc_now()
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[AUDIT LOG ERROR] Failed to record audit log: {e}")

def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Helper for resolving current user from cryptographically verified HMAC session token."""
    token = request.cookies.get("session_token")
    if token:
        user_id = verify_session_token(token)
        if user_id:
            try:
                u = db.query(User).filter(User.id == user_id).first()
                if u and u.status == "Active":
                    return u
            except Exception:
                pass

    return None

def require_admin(request: Request, user: Optional[User] = Depends(get_current_user)) -> User:
    """Dependency requiring active admin role."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Official authentication required.")
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: System Administrator privileges required."
        )
    return user

def require_supervisor(request: Request, user: Optional[User] = Depends(get_current_user)) -> User:
    """Dependency requiring active supervisory officer or admin role."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Official authentication required.")
    if user.role not in ["officer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Supervisory Enforcement privileges required."
        )
    return user
