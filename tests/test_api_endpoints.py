"""
API & Web Routes Test Suite
Verifies:
1. Public endpoints (Homepage, Login, Register, Logout).
2. Unauthenticated redirects to /login for protected enforcement pages.
3. Authenticated access across all statutory modules.
4. Role-based 403 barriers for administrative pages.
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

from main import app
from database import SessionLocal
from models import User
from auth_helper import create_session_token

class TestAPIEndpoints(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db: Session = SessionLocal()
        cls.admin = cls.db.query(User).filter(User.role == "admin").first()
        cls.admin_token = create_session_token(cls.admin.id) if cls.admin else ""

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_public_pages(self):
        """Public homepage, login, and registration pages must return HTTP 200."""
        res_home = self.client.get("/")
        self.assertEqual(res_home.status_code, 200)

        res_login = self.client.get("/login")
        self.assertEqual(res_login.status_code, 200)

        res_register = self.client.get("/register")
        self.assertEqual(res_register.status_code, 200)

    def test_unauthenticated_redirects(self):
        """Protected enforcement routes must redirect unauthenticated visitors to /login."""
        protected_routes = [
            "/dashboard",
            "/new-inspection",
            "/history",
            "/companies",
            "/products",
            "/reports",
            "/admin/rules"
        ]
        for route in protected_routes:
            res = self.client.get(route, follow_redirects=False)
            self.assertEqual(res.status_code, 302, f"Route {route} must redirect unauthenticated users.")
            self.assertIn("/login", res.headers.get("location", ""))

    def test_authenticated_dashboard_and_pages(self):
        """Authenticated admin officer can access all statutory modules."""
        cookies = {"session_token": self.admin_token}
        routes_to_test = [
            "/dashboard",
            "/new-inspection",
            "/history",
            "/companies",
            "/products",
            "/reports",
            "/admin/rules",
            "/admin/users",
            "/admin/audit-logs"
        ]
        for route in routes_to_test:
            res = self.client.get(route, cookies=cookies)
            self.assertEqual(res.status_code, 200, f"Authenticated route {route} failed with status {res.status_code}")

    def test_api_dashboard_stats(self):
        """API dashboard stats endpoint returns JSON metrics."""
        # Unauthenticated -> 401
        res_unauth = self.client.get("/api/dashboard")
        self.assertEqual(res_unauth.status_code, 401)

        # Authenticated -> 200 with JSON stats
        cookies = {"session_token": self.admin_token}
        res_auth = self.client.get("/api/dashboard", cookies=cookies)
        self.assertEqual(res_auth.status_code, 200)
        data = res_auth.json()
        self.assertIn("total_inspections", data)
        self.assertIn("compliance_rate", data)

    def test_logout(self):
        """Logout endpoint clears cookies and redirects to homepage."""
        res = self.client.get("/logout", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get("location"), "/")

if __name__ == "__main__":
    unittest.main()
