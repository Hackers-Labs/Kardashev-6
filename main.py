import os
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Depends, Request, Form, File, UploadFile, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func

from database import engine, get_db, Base
from models import User, Company, Product, Inspection, InspectionField, Violation, Inquiry, AuditLog
from auth_helper import verify_password, hash_password, create_session_token, verify_session_token, validate_password_strength
from services.ocr_service import run_package_ocr
from services.gemini_service import extract_declarations_ai
from services.rule_engine import evaluate_declarations
from services.report_service import generate_pdf_report, generate_docx_report

# Initialize Tables if not yet created
Base.metadata.create_all(bind=engine)

def init_system_admin():
    """Ensures pre-defined Department System Administrator exists in the database."""
    from database import SessionLocal
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
                created_at=datetime.utcnow()
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

init_system_admin()

app = FastAPI(
    title="MetroLens - Legal Metrology Compliance Enforcement Portal",
    description="Department of Consumer Affairs, Government of India - Packaged Commodities Rules 2011 Enforcement Platform",
    version="2.0.0"
)

# Directories
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = STATIC_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
(UPLOADS_DIR / "annotated").mkdir(parents=True, exist_ok=True)
(UPLOADS_DIR / "reports").mkdir(parents=True, exist_ok=True)

# Mount Static Files & Templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def render(request: Request, name: str, context: dict = None, status_code: int = 200):
    ctx = context or {}
    return templates.TemplateResponse(request=request, name=name, context=ctx, status_code=status_code)

def log_audit_event(db: Session, action: str, details: str, user_id: Optional[int] = None, ip_address: Optional[str] = None):
    """Logs security and compliance events into the immutable AuditLog table (IT Act 2000 Section 65B)."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address or "127.0.0.1",
            created_at=datetime.utcnow()
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[AUDIT LOG ERROR] Failed to record audit log: {e}")

# Helper for current user from signed cookie/session
def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    # Cryptographically verified HMAC session token
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
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Official authentication required.")
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: System Administrator privileges required."
        )
    return user

def require_supervisor(request: Request, user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Official authentication required.")
    if user.role not in ["officer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Supervisory Enforcement privileges required."
        )
    return user

# ============================================================================
# WEB INTERFACE ROUTES (Minimal Official Government Portal)
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def public_homepage(request: Request, user: Optional[User] = Depends(get_current_user)):
    """Public Government Portal Homepage."""
    return render(request, "home.html", {
        "current_user": user,
        "page_title": "Department of Consumer Affairs | National Legal Metrology Enforcement Portal"
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user)
):
    if user:
        return RedirectResponse(url=next or "/dashboard", status_code=status.HTTP_302_FOUND)
    return render(request, "login.html", {"error": None, "next": next})

@app.post("/login", response_class=HTMLResponse)
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
        
        user.last_login = datetime.utcnow()
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

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: Optional[User] = Depends(get_current_user)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return render(request, "register.html", {"error": None, "form": {}})

@app.post("/register", response_class=HTMLResponse)
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
        last_login=datetime.utcnow()
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

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="session_token")
    response.delete_cookie(key="user_id")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user:
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=status.HTTP_302_FOUND)

    # Role-aware metrics and feed
    if user.role in ["officer", "admin"]:
        # Supervisory / Admin: Central Department-Wide Surveillance Feed
        query = db.query(Inspection)
        total_inspections = query.count()
        compliant_count = query.filter(Inspection.overall_status == "COMPLIANT").count()
        non_compliant_count = query.filter(Inspection.overall_status != "COMPLIANT").count()
        compliance_rate = round((compliant_count / total_inspections) * 100, 1) if total_inspections > 0 else 0.0
        recent = query.order_by(desc(Inspection.created_at)).limit(8).all()
        tier_label = "System Administration Tier • National Surveillance Feed" if user.role == "admin" else "Supervisory Oversight Tier • Central Jurisdiction Feed"
    else:
        # Field Inspector: Personal Audits Isolated Feed
        user_inspections = db.query(Inspection).filter(Inspection.inspector_id == user.id)
        total_inspections = user_inspections.count()
        compliant_count = user_inspections.filter(Inspection.overall_status == "COMPLIANT").count()
        non_compliant_count = user_inspections.filter(Inspection.overall_status != "COMPLIANT").count()
        compliance_rate = round((compliant_count / total_inspections) * 100, 1) if total_inspections > 0 else 0.0
        recent = user_inspections.order_by(desc(Inspection.created_at)).limit(6).all()
        tier_label = "Field Enforcement Tier • Personal Audit Monitor"

    stats = {
        "total_inspections": total_inspections,
        "compliant_count": compliant_count,
        "non_compliant_count": non_compliant_count,
        "compliance_rate": compliance_rate,
        "tier_label": tier_label
    }

    return render(request, "dashboard.html", {
        "current_user": user,
        "page_title": "Enforcement Dashboard",
        "active_nav": "dashboard",
        "stats": stats,
        "recent_inspections": recent
    })

@app.get("/new-inspection", response_class=HTMLResponse)
async def new_inspection_page(
    request: Request,
    user: Optional[User] = Depends(get_current_user)
):
    if not user:
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=status.HTTP_302_FOUND)

    return render(request, "new_inspection.html", {
        "current_user": user,
        "page_title": "New Package Scan",
        "active_nav": "new-inspection"
    })

@app.get("/inspections/{id}", response_class=HTMLResponse)
async def inspection_result_page(
    id: int,
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user:
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=status.HTTP_302_FOUND)

    inspection = db.query(Inspection).filter(Inspection.id == id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection report not found")

    # Security authorization: Inspector can only view their own scan unless supervisor or admin
    if inspection.inspector_id != user.id and user.role not in ["officer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You are not authorized to view this statutory inspection record."
        )

    try:
        extracted_data = json.loads(inspection.extracted_json) if inspection.extracted_json else {}
    except Exception:
        extracted_data = {}

    return render(request, "inspection_result.html", {
        "current_user": user,
        "page_title": f"Inspection #{inspection.inspection_number}",
        "active_nav": "history",
        "inspection": inspection,
        "extracted_data": extracted_data
    })

@app.get("/history", response_class=HTMLResponse)
async def history_page(
    request: Request,
    q: Optional[str] = None,
    status: Optional[str] = None,
    inspector_id: Optional[int] = None,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user:
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=302)

    query = db.query(Inspection)

    # Role enforcement: Inspectors see strictly own scans; Officers and Admins can view all
    if user.role == "inspector":
        query = query.filter(Inspection.inspector_id == user.id)
    elif inspector_id:
        query = query.filter(Inspection.inspector_id == inspector_id)

    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.join(Product, isouter=True).join(Company, isouter=True).filter(
            or_(
                Inspection.inspection_number.ilike(term),
                Product.product_name.ilike(term),
                Company.company_name.ilike(term)
            )
        )

    if status and status.strip():
        query = query.filter(Inspection.overall_status == status.strip())

    inspections = query.order_by(desc(Inspection.created_at)).all()
    all_inspectors = db.query(User).filter(User.role == "inspector").all() if user.role in ["officer", "admin"] else []

    return render(request, "inspection_history.html", {
        "current_user": user,
        "page_title": "Inspection History Log",
        "active_nav": "history",
        "inspections": inspections,
        "query": q or "",
        "selected_status": status or "",
        "selected_inspector": inspector_id,
        "all_inspectors": all_inspectors
    })

@app.get("/companies", response_class=HTMLResponse)
async def companies_page(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user:
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=status.HTTP_302_FOUND)

    if user.role in ["officer", "admin"]:
        companies = db.query(Company).all()
    else:
        companies = (
            db.query(Company)
            .join(Inspection, Inspection.company_id == Company.id)
            .filter(Inspection.inspector_id == user.id)
            .distinct()
            .all()
        )
    return render(request, "companies.html", {
        "current_user": user,
        "page_title": "Companies Directory",
        "active_nav": "companies",
        "companies": companies
    })

@app.get("/products", response_class=HTMLResponse)
async def products_page(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user:
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=status.HTTP_302_FOUND)

    if user.role in ["officer", "admin"]:
        products = db.query(Product).all()
    else:
        products = (
            db.query(Product)
            .join(Inspection, Inspection.product_id == Product.id)
            .filter(Inspection.inspector_id == user.id)
            .distinct()
            .all()
        )
    return render(request, "products.html", {
        "current_user": user,
        "page_title": "Product Repository",
        "active_nav": "products",
        "products": products
    })

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(
    request: Request,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user:
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=status.HTTP_302_FOUND)

    if user.role in ["officer", "admin"]:
        inspections = db.query(Inspection).order_by(desc(Inspection.created_at)).all()
    else:
        inspections = db.query(Inspection).filter(Inspection.inspector_id == user.id).order_by(desc(Inspection.created_at)).all()

    return render(request, "reports.html", {
        "current_user": user,
        "page_title": "Statutory Compliance Reports",
        "active_nav": "reports",
        "inspections": inspections
    })

# ============================================================================
# REST API ENDPOINTS (Core OCR, AI, Decision, Document Export)
# ============================================================================

@app.post("/api/scan")
async def scan_package_endpoint(
    request: Request,
    image: UploadFile = File(...),
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Core AI Pipeline:
    1. Saves uploaded image
    2. Runs OpenCV preprocessing + OCR + Readability Bounding Box Analysis
    3. Extracts statutory declarations using Gemini 2.5 Flash
    4. Evaluates Legal Metrology Rules 2011 (Rule 6)
    5. Persists inspection record in SQLite
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Official authentication required to initiate statutory package inspection."
        )

    # 1. Save uploaded image file
    ext = Path(image.filename).suffix or ".jpg"
    unique_filename = f"INS_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
    image_save_path = UPLOADS_DIR / unique_filename

    with open(image_save_path, "wb") as f:
        content = await image.read()
        f.write(content)

    # 2. Run OpenCV + OCR
    ocr_result = run_package_ocr(str(image_save_path), str(UPLOADS_DIR))
    raw_ocr_text = ocr_result.get("raw_text", "")
    detections = ocr_result.get("detections", [])
    annotated_url = ocr_result.get("annotated_image_url") or f"/static/uploads/annotated/{Path(unique_filename).stem}_annotated.jpg"

    # 3. Semantic Declaration Extraction (Gemini 3.6 Flash Multimodal Vision)
    extracted_declarations = extract_declarations_ai(raw_ocr_text, detections, image_path=str(image_save_path))

    # 4. Deterministic Legal Metrology Rule 6 Compliance Engine
    evaluation = evaluate_declarations(extracted_declarations)

    # 5. Persist Record to SQLite
    try:
        mfr_name = extracted_declarations.get("manufacturer") or "Unknown Manufacturer"
        prod_name = extracted_declarations.get("product_name") or "Packaged Commodity"
        brand_name = extracted_declarations.get("brand") or ""

        # Resolve or create Company
        company = db.query(Company).filter(Company.company_name.ilike(f"%{mfr_name[:30]}%")).first()
        if not company:
            company = Company(
                company_name=mfr_name[:150],
                address="Address extracted from retail package",
                status="Active"
            )
            db.add(company)
            db.flush()

        # Resolve or create Product
        product = db.query(Product).filter(
            Product.product_name.ilike(f"%{prod_name[:30]}%"),
            Product.company_id == company.id
        ).first()
        if not product:
            product = Product(
                company_id=company.id,
                product_name=prod_name[:150],
                brand_name=brand_name[:100],
                manufacturer_name=mfr_name[:150],
                category="Packaged Commodities"
            )
            db.add(product)
            db.flush()

        # Generate unique inspection number
        insp_number = f"INS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"

        # Comprehensive JSON payload storing all extracted text, detections, declarations & packaged food rules
        full_extraction_json = {
            "inspection_number": insp_number,
            "scan_timestamp": datetime.utcnow().isoformat(),
            "declarations": extracted_declarations,
            "all_extracted_text": extracted_declarations.get("all_extracted_text_segments") or [d["text"] for d in detections],
            "raw_ocr_stream": raw_ocr_text,
            "ocr_detections_count": len(detections),
            "ocr_detections": detections,
            "compliance_summary": {
                "overall_status": evaluation["overall_status"],
                "compliance_score": evaluation["compliance_score"],
                "risk_level": evaluation["risk_level"],
                "passed_count": evaluation["passed_declarations"],
                "total_rules": evaluation["total_declarations"]
            },
            "metrology_rules": evaluation.get("metrology_rules", []),
            "food_rules": evaluation.get("food_rules", []),
            "rules_evaluation": evaluation.get("rules_evaluation", []),
            "violations": evaluation["violations"]
        }

        inspection = Inspection(
            inspection_number=insp_number,
            company_id=company.id,
            product_id=product.id,
            inspector_id=user.id if user else 1,
            package_image_url=f"/static/uploads/{unique_filename}",
            annotated_image_url=annotated_url,
            raw_ocr_text=raw_ocr_text,
            extracted_json=json.dumps(full_extraction_json, ensure_ascii=False, indent=2),
            overall_status=evaluation["overall_status"],
            risk_level=evaluation["risk_level"],
            compliance_score=evaluation["compliance_score"],
            notes="Automated AI Scan & Statutory Packaged Food Rules Evaluation"
        )
        db.add(inspection)
        db.flush()

        # Save individual declaration fields with bounding boxes
        for r in evaluation["rules_evaluation"]:
            field_label = r["field"]
            category_prefix = "LM" if "Metrology" in r.get("category", "") else "FOOD"
            extracted_val = r["extracted_value"]

            # Match bounding box from OCR detections
            matched_bbox = None
            if extracted_val and str(extracted_val).strip() and str(extracted_val).lower() not in ["none", "null", "not stated"]:
                ev_str = str(extracted_val).lower()
                for d in detections:
                    d_txt = d.get("text", "").lower()
                    if d_txt and (d_txt in ev_str or ev_str in d_txt):
                        matched_bbox = d["bbox"]
                        break

            # Fallback to general bounding box if not exact
            if not matched_bbox and detections:
                matched_bbox = detections[0]["bbox"]

            field_obj = InspectionField(
                inspection_id=inspection.id,
                field_name=f"[{category_prefix}] {field_label}",
                extracted_value=str(extracted_val) if extracted_val is not None else "",
                field_status=r["status"],
                confidence_score=96.0 if r["pass"] else 0.0,
                bbox_json=json.dumps(matched_bbox) if matched_bbox else None
            )
            db.add(field_obj)

        # Save violations
        for v in evaluation["violations"]:
            viol_obj = Violation(
                inspection_id=inspection.id,
                rule_id=v["rule_id"],
                rule_name=v["rule_name"],
                field_name=v["field_name"],
                severity=v["severity"],
                penalty_amount=v["penalty_amount"],
                notes=v["notes"],
                status="Detected"
            )
            db.add(viol_obj)

        # Update Product compliance stats
        product.total_inspections += 1
        if evaluation["violations"]:
            product.total_violations += 1
        product.compliance_rate = round(
            ((product.total_inspections - product.total_violations) / product.total_inspections) * 100, 1
        )
        product.last_inspected_at = datetime.utcnow()

        db.commit()

        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_event(
            db, "PACKAGE_SCAN_COMPLETED",
            f"Statutory inspection #{inspection.inspection_number} completed: {inspection.overall_status} (Score: {inspection.compliance_score}%) for product '{product.product_name}'",
            user_id=user.id, ip_address=client_ip
        )

        return {
            "success": True,
            "inspection_id": inspection.id,
            "inspection_number": inspection.inspection_number,
            "overall_status": inspection.overall_status,
            "compliance_score": inspection.compliance_score
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database save error: {str(e)}")

@app.patch("/api/inspections/{id}/decision")
async def update_inspector_decision(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    """
    Saves the official human inspector decision ('confirmed', 'rejected', 'further_review')
    and remarks without overwriting the machine's original findings.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Official authentication required to record inspector decision."
        )

    payload = await request.json()
    decision = payload.get("decision")
    remarks = payload.get("remarks")

    inspection = db.query(Inspection).filter(Inspection.id == id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    if inspection.inspector_id != user.id and user.role not in ["officer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You are not authorized to record decisions on this inspection."
        )

    inspection.inspector_decision = decision
    inspection.inspector_remarks = remarks
    db.commit()

    return {"success": True, "message": "Inspector decision recorded successfully."}

@app.get("/api/reports/{id}/pdf")
async def download_pdf(
    id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    """Downloads official sealed PDF compliance report generated by ReportLab."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Official authentication required to download inspection report."
        )

    inspection = db.query(Inspection).filter(Inspection.id == id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    if inspection.inspector_id != user.id and user.role not in ["officer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You are not authorized to export this statutory report."
        )

    pdf_filename = f"Inspection_Report_{inspection.inspection_number}.pdf"
    pdf_path = str(UPLOADS_DIR / "reports" / pdf_filename)

    generate_pdf_report(inspection, inspection.fields, inspection.violations, pdf_path)

    return FileResponse(
        pdf_path,
        filename=pdf_filename,
        media_type="application/pdf"
    )

@app.get("/api/reports/{id}/docx")
async def download_docx(
    id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    """Downloads official editable Microsoft Word (.docx) report generated by python-docx."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Official authentication required to download inspection report."
        )

    inspection = db.query(Inspection).filter(Inspection.id == id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    if inspection.inspector_id != user.id and user.role not in ["officer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You are not authorized to export this statutory report."
        )

    docx_filename = f"Inspection_Report_{inspection.inspection_number}.docx"
    docx_path = str(UPLOADS_DIR / "reports" / docx_filename)

    generate_docx_report(inspection, inspection.fields, inspection.violations, docx_path)

    return FileResponse(
        docx_path,
        filename=docx_filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@app.get("/api/inspections/{id}/json")
async def download_inspection_json(
    id: int,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    """Exports the entire comprehensive extracted package text, detections, and statutory findings as JSON."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Official authentication required to export evidence."
        )

    inspection = db.query(Inspection).filter(Inspection.id == id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found")

    if inspection.inspector_id != user.id and user.role not in ["officer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: You are not authorized to export this statutory inspection evidence."
        )

    try:
        data = json.loads(inspection.extracted_json) if inspection.extracted_json else {}
    except Exception:
        data = {"raw_ocr_text": inspection.raw_ocr_text, "extracted_json": inspection.extracted_json}

    return JSONResponse(
        content=data,
        headers={"Content-Disposition": f"attachment; filename=Inspection_{inspection.inspection_number}_Extracted_Evidence.json"}
    )

@app.get("/api/dashboard")
async def api_dashboard_stats(
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user)
):
    """API endpoint for live dashboard data scoped to the officer."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Official authentication required."
        )

    user_inspections = db.query(Inspection).filter(Inspection.inspector_id == user.id)
    total = user_inspections.count()
    compliant = user_inspections.filter(Inspection.overall_status == "COMPLIANT").count()
    non_compliant = user_inspections.filter(Inspection.overall_status != "COMPLIANT").count()
    rate = round((compliant / total) * 100, 1) if total > 0 else 0.0

    return {
        "total_inspections": total,
        "compliant_count": compliant,
        "non_compliant_count": non_compliant,
        "compliance_rate": rate
    }

# ============================================================================
# SYSTEM ADMINISTRATION & STATUTORY GOVERNANCE (ADMIN ONLY)
# ============================================================================

@app.get("/admin/users", response_class=HTMLResponse)
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

@app.post("/api/admin/users/{id}/toggle-status")
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

@app.post("/api/admin/users/{id}/change-role")
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

@app.post("/api/admin/users/create")
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
        created_at=datetime.utcnow()
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

@app.get("/admin/audit-logs", response_class=HTMLResponse)
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

@app.get("/admin/rules", response_class=HTMLResponse)
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

@app.post("/api/inspections/{id}/compound")
async def compound_inspection(
    id: int,
    request: Request,
    user: User = Depends(require_supervisor),
    db: Session = Depends(get_db)
):
    """
    Supervisory Quasi-Judicial Adjudication & Section 48 Compounding Order.
    Permitted only for Supervisory Officers and System Administrators.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    inspection = db.query(Inspection).filter(Inspection.id == id).first()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection record not found.")

    payload = await request.json()
    status_val = payload.get("adjudication_status")
    fee_val = payload.get("compounding_fee")
    notes_val = payload.get("adjudication_notes")

    if status_val not in ["CONFIRMED_VIOLATION", "COMPOUNDED_SEC_48", "WARNING_ISSUED", "DISMISSED"]:
        raise HTTPException(status_code=400, detail="Invalid adjudication status.")

    try:
        fee = float(fee_val) if fee_val is not None and str(fee_val).strip() != "" else 0.0
    except (ValueError, TypeError):
        fee = 0.0

    inspection.adjudication_status = status_val
    inspection.compounding_fee = fee
    inspection.adjudication_notes = notes_val
    inspection.adjudicated_by_id = user.id
    inspection.adjudicated_at = datetime.utcnow()
    db.commit()

    log_audit_event(
        db, "SECTION_48_COMPOUNDING_ORDER",
        f"Inspection #{inspection.inspection_number} adjudicated: {status_val}, Compounding Fee: ₹{fee:.2f} by {user.designation} {user.full_name}",
        user_id=user.id, ip_address=client_ip
    )

    return {
        "success": True,
        "message": f"Statutory order registered under Section 48: {status_val}",
        "adjudication_status": status_val,
        "compounding_fee": fee,
        "adjudicated_by": user.full_name
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

