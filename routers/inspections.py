import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User, Company, Product, Inspection, InspectionField, Violation, utc_now
from dependencies import (
    render,
    log_audit_event,
    get_current_user,
    require_supervisor,
    UPLOADS_DIR
)
from services.ocr_service import run_package_ocr
from services.gemini_service import extract_declarations_ai
from services.rule_engine import evaluate_declarations
from services.report_service import generate_pdf_report, generate_docx_report

router = APIRouter(tags=["Inspections & Compliance"])

@router.get("/new-inspection", response_class=HTMLResponse)
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

@router.get("/inspections/{id}", response_class=HTMLResponse)
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

@router.post("/api/scan")
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
    3. Extracts statutory declarations using Gemini Flash Vision
    4. Evaluates Legal Metrology Rules 2011 (Rule 6) & packaged food rules
    5. Persists inspection record in SQLite
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Official authentication required to initiate statutory package inspection."
        )

    # 1. Save uploaded image file
    ext = Path(image.filename).suffix or ".jpg"
    unique_filename = f"INS_{utc_now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
    image_save_path = UPLOADS_DIR / unique_filename

    with open(image_save_path, "wb") as f:
        content = await image.read()
        f.write(content)

    # 2. Run OpenCV + OCR
    ocr_result = run_package_ocr(str(image_save_path), str(UPLOADS_DIR))
    raw_ocr_text = ocr_result.get("raw_text", "")
    detections = ocr_result.get("detections", [])
    annotated_url = ocr_result.get("annotated_image_url") or f"/static/uploads/annotated/{Path(unique_filename).stem}_annotated.jpg"

    # 3. Semantic Declaration Extraction (Gemini Multimodal Vision)
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
        insp_number = f"INS-{utc_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"

        # Comprehensive JSON payload storing all extracted text, detections, declarations & packaged food rules
        full_extraction_json = {
            "inspection_number": insp_number,
            "scan_timestamp": utc_now().isoformat(),
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
        product.last_inspected_at = utc_now()

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

@router.patch("/api/inspections/{id}/decision")
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

@router.post("/api/inspections/{id}/compound")
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
    inspection.adjudicated_at = utc_now()
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

@router.get("/api/reports/{id}/pdf")
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

@router.get("/api/reports/{id}/docx")
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

@router.get("/api/inspections/{id}/json")
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
