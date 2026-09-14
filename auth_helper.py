import hashlib
import hmac
import os
import time
from typing import Optional

SECRET_KEY = os.getenv("SESSION_SECRET", "metrolens-doca-gov-in-secret-key-2026-auth").encode("utf-8")

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Enforces strong password policy for official government portal:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one numerical digit
    - At least one special character
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit (0-9)."
    special_chars = set("!@#$%^&*()_+-=[]{}|;:,.<>?/~`'\"\\")
    if not any(c in special_chars for c in password):
        return False, "Password must contain at least one special character (!@#$%^&*)."
    return True, ""

def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt."""
    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return f"pbkdf2:sha256:100000${salt}${key}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a password against stored PBKDF2 or legacy salt$sha256 using constant-time comparison."""
    if not stored_hash or "$" not in stored_hash:
        return False
    try:
        if stored_hash.startswith("pbkdf2:sha256:"):
            parts = stored_hash.split("$")
            if len(parts) == 3:
                iterations = int(parts[0].split(":")[2])
                salt = parts[1]
                expected_key = parts[2]
                computed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations).hex()
                return hmac.compare_digest(expected_key, computed)
        elif "$" in stored_hash:
            salt, hashed = stored_hash.split("$", 1)
            expected = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
            return hmac.compare_digest(expected, hashed)
    except Exception:
        return False
    return False

def create_session_token(user_id: int) -> str:
    """Creates a cryptographically signed session token with HMAC-SHA256."""
    timestamp = str(int(time.time()))
    payload = f"{user_id}:{timestamp}".encode("utf-8")
    signature = hmac.new(SECRET_KEY, payload, hashlib.sha256).hexdigest()
    return f"{user_id}.{timestamp}.{signature}"

def verify_session_token(token: str, max_age_seconds: int = 86400 * 7) -> Optional[int]:
    """Verifies HMAC signature and expiration on session token. Returns user_id if valid."""
    if not token or "." not in token:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None
    user_id_str, timestamp_str, signature = parts
    try:
        timestamp = int(timestamp_str)
        # Check expiration
        if (time.time() - timestamp) > max_age_seconds:
            return None
        payload = f"{user_id_str}:{timestamp_str}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY, payload, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected_sig, signature):
            return int(user_id_str)
    except Exception:
        return None
    return None


