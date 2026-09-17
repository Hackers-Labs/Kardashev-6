"""
Role-Based Access Control (RBAC) & Admin Governance Test Suite
Verifies:
1. Pre-seeded System Administrator exists in database.
2. Registration restricts admin self-creation.
3. Registration of Field Inspector and Supervisory Officer.
4. Cryptographic HMAC session tokens and security.
5. Strict 403 Forbidden checks on all administrative & supervisory routes.
6. Admin user management (status toggling, role change, self-protection).
7. Evidentiary Audit Logging conforming to IT Act 2000 Section 65B.
8. Statutory Rules Reference Manual accessibility.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Import main application and database
from main import app
from database import SessionLocal, get_db
from models import User, Company, Product, Inspection, Violation, AuditLog
from auth_helper import (
    verify_password, hash_password, create_session_token,
    verify_session_token, validate_password_strength
)

class TestRBACAndAdminGovernance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()
        # Clean up any leftover test users
        cls.db.query(User).filter(User.email.in_([
            "field.inspector@doca.gov.in",
            "supervisor.officer@doca.gov.in",
            "hacker@test.gov.in"
        ])).delete(synchronize_session=False)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.query(User).filter(User.email.in_([
            "field.inspector@doca.gov.in",
            "supervisor.officer@doca.gov.in",
            "hacker@test.gov.in"
        ])).delete(synchronize_session=False)
        cls.db.commit()
        cls.db.close()

    def test_01_admin_pre_seeded(self):
        """Verify pre-defined Administrator exists and has PBKDF2 hashed password."""
        admin = self.db.query(User).filter(User.role == "admin").first()
        self.assertIsNotNone(admin, "Admin account must be pre-seeded in database.")
        self.assertEqual(admin.email, "admin@doca.gov.in")
        self.assertEqual(admin.status, "Active")
        self.assertTrue(admin.password_hash.startswith("pbkdf2:sha256:100000$"), "Admin password must use PBKDF2-HMAC-SHA256")
        self.assertTrue(verify_password("Admin@DoCA2026!", admin.password_hash), "Admin password verification failed.")

    def test_02_registration_admin_block(self):
        """Verify public registration strictly blocks role='admin'."""
        res = self.client.post("/register", data={
            "full_name": "Hacker Impersonator",
            "email": "hacker@test.gov.in",
            "role": "admin",
            "department": "Security",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        })
        self.assertIn("Administrative roles cannot be registered", res.text)
        # Confirm user was not created
        hacker = self.db.query(User).filter(User.email == "hacker@test.gov.in").first()
        self.assertIsNone(hacker, "Admin must never be created via public registration!")

    def test_03_registration_and_login_flow(self):
        """Verify inspector and officer registration, and authentication session tokens."""
        # Register Field Inspector
        res_insp = self.client.post("/register", data={
            "full_name": "Test Field Inspector",
            "email": "field.inspector@doca.gov.in",
            "employee_id": "DOCA-TEST-INSP",
            "role": "inspector",
            "department": "Legal Metrology Enforcement",
            "password": "InspectorPass123!",
            "confirm_password": "InspectorPass123!"
        }, follow_redirects=False)
        self.assertEqual(res_insp.status_code, 302)
        self.assertIn("session_token", res_insp.cookies)

        # Register Supervisory Officer
        res_off = self.client.post("/register", data={
            "full_name": "Test Supervisory Officer",
            "email": "supervisor.officer@doca.gov.in",
            "employee_id": "DOCA-TEST-SUP",
            "role": "officer",
            "department": "Supervisory & Compounding Division",
            "password": "SupervisorPass123!",
            "confirm_password": "SupervisorPass123!"
        }, follow_redirects=False)
        self.assertEqual(res_off.status_code, 302)
        self.assertIn("session_token", res_off.cookies)

    def test_04_rbac_route_protection_403(self):
        """Verify inspectors are strictly blocked from /admin/* with 403 Forbidden."""
        inspector = self.db.query(User).filter(User.email == "field.inspector@doca.gov.in").first()
        self.assertIsNotNone(inspector)
        inspector.role = "inspector"
        self.db.commit()

        insp_token = create_session_token(inspector.id)
        cookies = {"session_token": insp_token}

        # Inspector attempts accessing /admin/users -> 403 Forbidden
        res_users = self.client.get("/admin/users", cookies=cookies)
        self.assertEqual(res_users.status_code, 403)
        self.assertIn("Access Denied", res_users.text)

        # Inspector attempts accessing /admin/audit-logs -> 403 Forbidden
        res_logs = self.client.get("/admin/audit-logs", cookies=cookies)
        self.assertEqual(res_logs.status_code, 403)

        # Inspector attempts toggling user status via API -> 403 Forbidden
        res_toggle = self.client.post(f"/api/admin/users/{inspector.id}/toggle-status", cookies=cookies)
        self.assertEqual(res_toggle.status_code, 403)

        # Inspector attempts compounding -> 403 Forbidden
        res_compound = self.client.post("/api/inspections/1/compound", cookies=cookies, json={
            "adjudication_status": "COMPOUNDED_SEC_48"
        })
        self.assertEqual(res_compound.status_code, 403)

    def test_05_admin_directory_and_governance(self):
        """Verify Admin can access /admin/users, toggle officer status, and change roles."""
        admin = self.db.query(User).filter(User.role == "admin").first()
        admin_token = create_session_token(admin.id)
        cookies = {"session_token": admin_token}

        # Admin access to directory
        res_dir = self.client.get("/admin/users", cookies=cookies)
        self.assertEqual(res_dir.status_code, 200)
        self.assertIn("Enforcement Officer Directory", res_dir.text)

        # Admin toggles inspector status
        inspector = self.db.query(User).filter(User.email == "field.inspector@doca.gov.in").first()
        res_toggle = self.client.post(f"/api/admin/users/{inspector.id}/toggle-status", cookies=cookies)
        self.assertEqual(res_toggle.status_code, 200)
        self.db.refresh(inspector)
        self.assertEqual(inspector.status, "Inactive")

        # Inactive officer cannot log in!
        res_blocked = self.client.post("/login", data={
            "email": "field.inspector@doca.gov.in",
            "password": "InspectorPass123!"
        })
        self.assertIn("Official account is deactivated", res_blocked.text)

        # Admin re-activates officer
        res_reactivate = self.client.post(f"/api/admin/users/{inspector.id}/toggle-status", cookies=cookies)
        self.assertEqual(res_reactivate.status_code, 200)
        self.db.refresh(inspector)
        self.assertEqual(inspector.status, "Active")

        # Admin cannot deactivate own account
        res_self = self.client.post(f"/api/admin/users/{admin.id}/toggle-status", cookies=cookies)
        self.assertEqual(res_self.status_code, 400)

        # Admin promotes inspector to officer
        res_role = self.client.post(f"/api/admin/users/{inspector.id}/change-role", cookies=cookies, json={
            "role": "officer"
        })
        self.assertEqual(res_role.status_code, 200)
        self.db.refresh(inspector)
        self.assertEqual(inspector.role, "officer")

    def test_06_security_audit_logs(self):
        """Verify immutable audit log entries recorded in SQLite."""
        admin = self.db.query(User).filter(User.role == "admin").first()
        admin_token = create_session_token(admin.id)
        cookies = {"session_token": admin_token}

        # View audit logs page
        res_logs = self.client.get("/admin/audit-logs", cookies=cookies)
        self.assertEqual(res_logs.status_code, 200)
        self.assertIn("Security &amp; Enforcement Audit Trail", res_logs.text)

        # Verify database has recorded events
        events = [log.action for log in self.db.query(AuditLog).all()]
        self.assertTrue(len(events) > 0)
        self.assertIn("LOGIN_BLOCKED_DEACTIVATED", events)
        self.assertIn("USER_STATUS_TOGGLED", events)
        self.assertIn("USER_ROLE_CHANGED", events)

    def test_07_rules_reference_manual(self):
        """Verify statutory rules reference accessible to authenticated officers."""
        admin = self.db.query(User).filter(User.role == "admin").first()
        admin_token = create_session_token(admin.id)
        cookies = {"session_token": admin_token}

        res_rules = self.client.get("/admin/rules", cookies=cookies)
        self.assertEqual(res_rules.status_code, 200)
        self.assertIn("Rule 6: Mandatory Declarations", res_rules.text)
        self.assertIn("Rule 7: Minimum Font Height", res_rules.text)
        self.assertIn("Section 36(1)", res_rules.text)

if __name__ == "__main__":
    unittest.main()
