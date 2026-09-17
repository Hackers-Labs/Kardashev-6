from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from database import get_db
from models import User, Company, Product, Inspection
from dependencies import render, get_current_user

router = APIRouter(tags=["Views & Dashboard"])

@router.get("/", response_class=HTMLResponse)
async def public_homepage(request: Request, user: Optional[User] = Depends(get_current_user)):
    """Public Government Portal Homepage."""
    return render(request, "home.html", {
        "current_user": user,
        "page_title": "Department of Consumer Affairs | National Legal Metrology Enforcement Portal"
    })

@router.get("/dashboard", response_class=HTMLResponse)
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

@router.get("/history", response_class=HTMLResponse)
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

@router.get("/companies", response_class=HTMLResponse)
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

@router.get("/products", response_class=HTMLResponse)
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

@router.get("/reports", response_class=HTMLResponse)
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

@router.get("/api/dashboard")
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
