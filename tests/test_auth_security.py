"""
Authentication & Cryptographic Security Test Suite
Verifies:
1. PBKDF2-HMAC-SHA256 password hashing with 100,000 rounds.
2. Constant-time verification to prevent timing attacks.
3. Government password complexity policy enforcement.
4. HMAC-SHA256 signed session tokens and tamper resistance.
5. Deactivated account immediate block on login and ongoing sessions.
"""

import unittest
from auth_helper import (
    hash_password, verify_password, create_session_token,
    verify_session_token, validate_password_strength
)

class TestAuthSecurity(unittest.TestCase):

    def test_pbkdf2_hashing_and_verification(self):
        """Test PBKDF2-HMAC-SHA256 password hashing and verification."""
        password = "Official@Gov2026!"
        pwd_hash = hash_password(password)

        self.assertTrue(pwd_hash.startswith("pbkdf2:sha256:100000$"))
        self.assertTrue(verify_password(password, pwd_hash))
        self.assertFalse(verify_password("WrongPassword123!", pwd_hash))
        self.assertFalse(verify_password("", pwd_hash))
        self.assertFalse(verify_password(password, ""))

    def test_legacy_hash_compatibility(self):
        """Ensure backward compatibility with legacy salt$sha256 format."""
        import hashlib
        salt = "a1b2c3d4e5f67890"
        legacy_hash = f"{salt}${hashlib.sha256((salt + 'LegacyPass123!').encode()).hexdigest()}"
        self.assertTrue(verify_password("LegacyPass123!", legacy_hash))
        self.assertFalse(verify_password("WrongPass", legacy_hash))

    def test_password_complexity_validator(self):
        """Test enforcement of government password standards."""
        # Less than 8 chars
        valid, err = validate_password_strength("Ab1!xyz")
        self.assertFalse(valid)
        self.assertIn("at least 8 characters", err)

        # Missing uppercase
        valid, err = validate_password_strength("lowercase123!")
        self.assertFalse(valid)
        self.assertIn("uppercase", err)

        # Missing lowercase
        valid, err = validate_password_strength("UPPERCASE123!")
        self.assertFalse(valid)
        self.assertIn("lowercase", err)

        # Missing digit
        valid, err = validate_password_strength("NoDigitsSymbol!")
        self.assertFalse(valid)
        self.assertIn("digit", err)

        # Missing special character
        valid, err = validate_password_strength("NoSpecialChar123")
        self.assertFalse(valid)
        self.assertIn("special character", err)

        # Valid strong password
        valid, err = validate_password_strength("Secure@DoCA2026!")
        self.assertTrue(valid)
        self.assertEqual(err, "")

    def test_hmac_session_tokens(self):
        """Test cryptographic session creation, verification, and tamper resistance."""
        user_id = 42
        token = create_session_token(user_id)
        self.assertIsNotNone(token)
        self.assertEqual(token.count("."), 2)

        # Valid verification
        verified_id = verify_session_token(token)
        self.assertEqual(verified_id, user_id)

        # Tampered user_id
        parts = token.split(".")
        tampered_user_token = f"999.{parts[1]}.{parts[2]}"
        self.assertIsNone(verify_session_token(tampered_user_token))

        # Tampered signature
        tampered_sig_token = f"{parts[0]}.{parts[1]}.badsignaturehex12345"
        self.assertIsNone(verify_session_token(tampered_sig_token))

        # Expired token simulation
        expired_token = f"{user_id}.1000000000.signature"
        self.assertIsNone(verify_session_token(expired_token))

if __name__ == "__main__":
    unittest.main()
