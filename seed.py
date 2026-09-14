import json
from datetime import datetime, timedelta
from database import engine, SessionLocal, Base
from models import User, Company, Product, Inspection, InspectionField, Violation, Inquiry, AuditLog
from auth_helper import hash_password

def seed_database():
    print("Creating all database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if users already seeded
        if db.query(User).first():
            print("Database already contains records. Skipping seed.")
            return

        print("Seeding demo users...")
        officer = User(
            id=1,
            employee_id="OFF-2026-001",
            full_name="Chief Officer Vikram Malhotra",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            role="officer",
            department="Legal Metrology HQ",
            designation="Chief Enforcement Controller",
            office_region="Zone 1 - Headquarters",
            phone="+91 98111 22334",
            status="Active"
        )
        inspector = User(
            id=2,
            employee_id="INS-2026-101",
            full_name="Inspector Rajesh Sharma",
            email="officer@example.com",
            password_hash=hash_password("123456"),
            role="inspector",
            department="Legal Metrology Zone 1",
            designation="Senior Field Inspector",
            office_region="West Delhi Region",
            phone="+91 98765 43210",
            status="Active"
        )
        inspector2 = User(
            id=3,
            employee_id="INS-2026-102",
            full_name="Inspector Priya Patel",
            email="priya.p@gov.in",
            password_hash=hash_password("123456"),
            role="inspector",
            department="Legal Metrology Zone 2",
            designation="Field Inspector",
            office_region="South Mumbai Region",
            phone="+91 98222 33445",
            status="Active"
        )
        db.add_all([officer, inspector, inspector2])
        db.commit()

        print("Seeding companies...")
        c1 = Company(
            id=1,
            company_name="Parle Products Pvt. Ltd.",
            company_type="Manufacturer & Packer",
            address="Vile Parle East, Mumbai - 400057, Maharashtra",
            phone="1800-22-1080",
            email="customercare@parle.biz",
            website="www.parleproducts.com",
            status="Active"
        )
        c2 = Company(
            id=2,
            company_name="PepsiCo India Holdings Pvt. Ltd.",
            company_type="Manufacturer & Packer",
            address="Level 3-6, Pioneer Square, Sector 62, Gurugram - 122001, Haryana",
            phone="1800-22-4466",
            email="feedback@pepsico.com",
            website="www.pepsicoindia.co.in",
            status="Active"
        )
        c3 = Company(
            id=3,
            company_name="Tata Consumer Products Limited",
            company_type="Manufacturer & Packer",
            address="1 Bishop Lefroy Road, Kolkata - 700020, West Bengal",
            phone="1800-108-4488",
            email="care@tataconsumer.com",
            website="www.tataconsumer.com",
            status="Active"
        )
        c4 = Company(
            id=4,
            company_name="Britannia Industries Ltd.",
            company_type="Manufacturer & Packer",
            address="5A Hungerford Street, Kolkata - 700017, West Bengal",
            phone="1800-425-4449",
            email="feedback@britaindia.com",
            website="www.britannia.co.in",
            status="Active"
        )
        db.add_all([c1, c2, c3, c4])
        db.commit()

        print("Seeding products...")
        p1 = Product(
            id=1,
            company_id=1,
            gtin_barcode="8901030000011",
            product_name="Parle-G Original Glucose Biscuits (250g)",
            brand_name="Parle-G",
            category="Packaged Foods & Biscuits",
            manufacturer_name="Parle Products Pvt. Ltd.",
            total_inspections=4,
            total_violations=0,
            compliance_rate=100.0,
            last_inspected_at=datetime.utcnow() - timedelta(days=2)
        )
        p2 = Product(
            id=2,
            company_id=2,
            gtin_barcode="8901491100022",
            product_name="Kurkure Masala Munch (90g)",
            brand_name="Kurkure",
            category="Packaged Foods & Snacks",
            manufacturer_name="PepsiCo India Holdings Pvt. Ltd.",
            total_inspections=3,
            total_violations=1,
            compliance_rate=66.7,
            last_inspected_at=datetime.utcnow() - timedelta(days=3)
        )
        p3 = Product(
            id=3,
            company_id=3,
            gtin_barcode="8901058000033",
            product_name="Tata Salt Vacuum Evaporated Iodized Salt (1kg)",
            brand_name="Tata Salt",
            category="Packaged Foods & Spices",
            manufacturer_name="Tata Consumer Products Limited",
            total_inspections=3,
            total_violations=0,
            compliance_rate=100.0,
            last_inspected_at=datetime.utcnow() - timedelta(days=7)
        )
        p4 = Product(
            id=4,
            company_id=4,
            gtin_barcode="8901063000044",
            product_name="Britannia Good Day Cashew Cookies (200g)",
            brand_name="Britannia",
            category="Packaged Foods & Biscuits",
            manufacturer_name="Britannia Industries Ltd.",
            total_inspections=2,
            total_violations=0,
            compliance_rate=100.0,
            last_inspected_at=datetime.utcnow() - timedelta(days=12)
        )
        db.add_all([p1, p2, p3, p4])
        db.commit()

        print("Seeding past inspections...")
        ins1 = Inspection(
            id=1,
            inspection_number="INS-20260905-00101",
            company_id=1,
            product_id=1,
            inspector_id=2,
            inspection_type="Routine Market Inspection",
            package_image_url="assets/Food.png",
            raw_ocr_text="PARLE-G ORIGINAL GLUCOSE BISCUITS\nNet Wt: 250 g\nMFR: Parle Products Pvt Ltd, Vile Parle East, Mumbai 400057\nMRP: Rs. 30.00\nPkd Date: 08/2026\nConsumer Care: 1800-22-1080",
            overall_status="COMPLIANT",
            risk_level="LOW",
            compliance_score=100.0,
            inspector_decision="confirmed",
            inspector_remarks="All 7 mandatory declarations present and verified in compliant format.",
            notes="Routine surveillance check.",
            inspection_date=datetime.utcnow() - timedelta(days=2)
        )
        ins2 = Inspection(
            id=2,
            inspection_number="INS-20260904-00102",
            company_id=2,
            product_id=2,
            inspector_id=2,
            inspection_type="Market Surveillance Inspection",
            package_image_url="assets/Food.png",
            raw_ocr_text="KURKURE MASALA MUNCH\nNet Wt: 90 g\nMFR: PepsiCo India Holdings Pvt Ltd\nMRP: Rs. 20.00\nPkd Date: 08/2026\nBatch No: KK082026M",
            overall_status="POTENTIAL_NON_COMPLIANCE",
            risk_level="HIGH",
            compliance_score=71.4,
            inspector_decision="confirmed",
            inspector_remarks="Consumer care email address missing on package label under Rule 6(2). Show-cause notice issued.",
            notes="Notice issued under Section 18 of Legal Metrology Act.",
            inspection_date=datetime.utcnow() - timedelta(days=3)
        )
        ins3 = Inspection(
            id=3,
            inspection_number="INS-20260828-00103",
            company_id=3,
            product_id=3,
            inspector_id=3,
            inspection_type="Citizen Complaint Audit",
            package_image_url="assets/Food.png",
            raw_ocr_text="TATA SALT VACUUM EVAPORATED IODIZED SALT\nNet Wt: 1 kg\nMFR: Tata Consumer Products Ltd\nMRP: Rs. 28.00\nPkd Date: 07/2026",
            overall_status="COMPLIANT",
            risk_level="LOW",
            compliance_score=100.0,
            inspector_decision="confirmed",
            inspector_remarks="Verification confirmed all statutory details compliant.",
            inspection_date=datetime.utcnow() - timedelta(days=7)
        )
        db.add_all([ins1, ins2, ins3])
        db.commit()

        # Seed Inspection Fields
        fields1 = [
            InspectionField(inspection_id=1, field_name="Manufacturer Details", expected_value="Parle Products Pvt Ltd", extracted_value="Parle Products Pvt Ltd, Vile Parle East, Mumbai 400057", field_status="Verified", confidence_score=98.0, bbox_json="[100, 150, 400, 185]"),
            InspectionField(inspection_id=1, field_name="Product Name", expected_value="Parle-G", extracted_value="Parle-G Original Glucose Biscuits", field_status="Verified", confidence_score=99.0, bbox_json="[120, 80, 450, 125]"),
            InspectionField(inspection_id=1, field_name="Net Quantity", expected_value="250 g", extracted_value="250 g", field_status="Verified", confidence_score=98.0, bbox_json="[450, 300, 560, 330]"),
            InspectionField(inspection_id=1, field_name="MRP", expected_value="₹30.00", extracted_value="₹30.00", field_status="Verified", confidence_score=97.0, bbox_json="[450, 350, 580, 380]"),
            InspectionField(inspection_id=1, field_name="Manufacturing Date", expected_value="08/2026", extracted_value="08/2026", field_status="Verified", confidence_score=95.0, bbox_json="[300, 400, 420, 430]"),
            InspectionField(inspection_id=1, field_name="Consumer Care", expected_value="1800-22-1080", extracted_value="1800-22-1080", field_status="Verified", confidence_score=96.0, bbox_json="[200, 460, 450, 490]"),
            InspectionField(inspection_id=1, field_name="Country of Origin", expected_value="India", extracted_value="India", field_status="Verified", confidence_score=98.0, bbox_json="[200, 510, 320, 540]"),
        ]
        fields2 = [
            InspectionField(inspection_id=2, field_name="Manufacturer Details", extracted_value="PepsiCo India Holdings Pvt. Ltd.", field_status="Verified", confidence_score=94.0, bbox_json="[80, 120, 380, 155]"),
            InspectionField(inspection_id=2, field_name="Net Quantity", extracted_value="90 g", field_status="Verified", confidence_score=96.0, bbox_json="[350, 280, 460, 310]"),
            InspectionField(inspection_id=2, field_name="MRP", extracted_value="₹20.00", field_status="Verified", confidence_score=95.0, bbox_json="[350, 320, 470, 350]"),
            InspectionField(inspection_id=2, field_name="Consumer Care Email", extracted_value="", field_status="Missing", confidence_score=0.0, bbox_json=None),
        ]
        db.add_all(fields1 + fields2)

        # Seed Violation
        viol1 = Violation(
            inspection_id=2,
            rule_id="RULE_6_2",
            rule_name="Rule 6(2) - Consumer Grievance Contact",
            field_name="Consumer Care Email",
            severity="High",
            penalty_amount=15000.0,
            notes="Consumer care email address not printed on retail package label.",
            status="Notice Issued"
        )
        db.add(viol1)

        # Seed Inquiry
        inq1 = Inquiry(
            id=1,
            inquiry_number="INQ-20260904-001",
            company_id=2,
            product_id=2,
            inspection_id=2,
            inspector_id=2,
            manufacturer_name="PepsiCo India Holdings Pvt. Ltd.",
            subject="Notice under Rule 6(2) of Legal Metrology Packaged Commodities Rules 2011",
            description="Non-compliance detected during inspection INS-20260904-00102 regarding missing consumer care email declaration.",
            response_deadline=datetime.utcnow() + timedelta(days=14),
            status="Issued"
        )
        db.add(inq1)

        db.commit()
        print("Database initialized and seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
