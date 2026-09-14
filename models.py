from datetime import datetime
import json
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="inspector")  # 'officer' or 'inspector'
    department = Column(String(100), default="Legal Metrology Enforcement")
    designation = Column(String(100), default="Inspector")
    office_region = Column(String(100), default="Zone 1 - Headquarters")
    phone = Column(String(20), nullable=True)
    status = Column(String(20), default="Active")  # 'Active', 'Inactive', 'Suspended'
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    inspections = relationship("Inspection", foreign_keys="[Inspection.inspector_id]", back_populates="inspector")
    inquiries = relationship("Inquiry", back_populates="inspector")

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(150), unique=True, index=True, nullable=False)
    company_type = Column(String(100), default="Manufacturer & Packer")
    address = Column(Text, nullable=False)
    phone = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    website = Column(String(150), nullable=True)
    status = Column(String(50), default="Active")
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="company")
    inspections = relationship("Inspection", back_populates="company")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    gtin_barcode = Column(String(50), index=True, nullable=True)
    product_name = Column(String(150), nullable=False)
    brand_name = Column(String(100), nullable=True)
    category = Column(String(100), default="Packaged Commodities")
    manufacturer_name = Column(String(150), nullable=False)
    total_inspections = Column(Integer, default=0)
    total_violations = Column(Integer, default=0)
    compliance_rate = Column(Float, default=100.0)
    last_inspected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="products")
    inspections = relationship("Inspection", back_populates="product")

class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    inspection_number = Column(String(50), unique=True, index=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    inspection_type = Column(String(100), default="Routine Market Inspection")
    package_image_url = Column(String(500), nullable=True)
    annotated_image_url = Column(String(500), nullable=True)
    raw_ocr_text = Column(Text, nullable=True)
    extracted_json = Column(Text, nullable=True)  # JSON-encoded declarations & findings
    overall_status = Column(String(50), default="COMPLIANT")  # 'COMPLIANT', 'POTENTIAL_NON_COMPLIANCE', 'REVIEW_REQUIRED'
    risk_level = Column(String(20), default="LOW")  # 'LOW', 'MEDIUM', 'HIGH'
    compliance_score = Column(Float, default=100.0)
    inspector_decision = Column(String(50), nullable=True)  # 'confirmed', 'rejected', 'further_review'
    inspector_remarks = Column(Text, nullable=True)
    adjudication_status = Column(String(50), nullable=True)  # 'CONFIRMED_VIOLATION', 'COMPOUNDED_SEC_48', 'WARNING_ISSUED', 'DISMISSED'
    adjudication_notes = Column(Text, nullable=True)
    compounding_fee = Column(Float, nullable=True)
    adjudicated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    adjudicated_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    inspection_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def resolved_annotated_image_url(self) -> str:
        if self.annotated_image_url:
            return self.annotated_image_url
        if self.package_image_url:
            from pathlib import Path
            p = Path(self.package_image_url)
            return f"/static/uploads/annotated/{p.stem}_annotated.jpg"
        return "/static/images/placeholder.jpg"

    inspector = relationship("User", foreign_keys=[inspector_id], back_populates="inspections")
    adjudicator = relationship("User", foreign_keys=[adjudicated_by_id])
    company = relationship("Company", back_populates="inspections")
    product = relationship("Product", back_populates="inspections")
    fields = relationship("InspectionField", back_populates="inspection", cascade="all, delete-orphan")
    violations = relationship("Violation", back_populates="inspection", cascade="all, delete-orphan")

class InspectionField(Base):
    __tablename__ = "inspection_fields"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(100), nullable=False)
    expected_value = Column(Text, nullable=True)
    extracted_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    field_status = Column(String(50), default="Verified")  # 'Verified', 'Missing', 'Review Required'
    confidence_score = Column(Float, default=95.0)
    bbox_json = Column(Text, nullable=True)  # [x1, y1, x2, y2]

    inspection = relationship("Inspection", back_populates="fields")

class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(String(50), nullable=True)
    rule_name = Column(String(150), nullable=False)
    field_name = Column(String(100), nullable=False)
    severity = Column(String(20), default="Medium")  # 'Low', 'Medium', 'High', 'Critical'
    penalty_amount = Column(Float, default=10000.0)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="Detected")  # 'Detected', 'Confirmed', 'Resolved'
    created_at = Column(DateTime, default=datetime.utcnow)

    inspection = relationship("Inspection", back_populates="violations")

class Inquiry(Base):
    __tablename__ = "inquiries"

    id = Column(Integer, primary_key=True, index=True)
    inquiry_number = Column(String(50), unique=True, index=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id", ondelete="SET NULL"), nullable=True)
    inspector_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    manufacturer_name = Column(String(150), nullable=False)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    response_deadline = Column(DateTime, nullable=True)
    manufacturer_response = Column(Text, nullable=True)
    status = Column(String(50), default="Issued")  # 'Issued', 'Responded', 'Resolved'
    issued_at = Column(DateTime, default=datetime.utcnow)

    inspector = relationship("User", back_populates="inquiries")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
