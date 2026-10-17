"""Authentication, cryptographic password hashing, and session tokens for OpcHub."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Optional, Tuple

# Secret key for session signature (read from environment or default dev secret)
SECRET_KEY = os.getenv("OPCHUB_SECRET_KEY", "opchub-default-maker-session-secret-key-2026")
SALT_LENGTH = 16
PBKDF2_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with cryptographically secure random salt."""
    salt = secrets.token_bytes(SALT_LENGTH)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    # Format: iterations$salt_b64$key_b64
    salt_b64 = base64.b64encode(salt).decode("ascii")
    key_b64 = base64.b64encode(key).decode("ascii")
    return f"{PBKDF2_ITERATIONS}${salt_b64}${key_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against PBKDF2 formatted hash string."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        iterations = int(parts[0])
        salt = base64.b64decode(parts[1].encode("ascii"))
        expected_key = base64.b64decode(parts[2].encode("ascii"))

        derived_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(derived_key, expected_key)
    except Exception:
        return False


def create_session_token(payload: Dict[str, Any], expires_in_seconds: int = 86400 * 7) -> str:
    """Create a signed, tamper-proof session token."""
    token_data = dict(payload)
    token_data["exp"] = int(time.time()) + expires_in_seconds
    token_data["iat"] = int(time.time())

    encoded_payload = base64.urlsafe_b64encode(
        json.dumps(token_data, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")

    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        encoded_payload.encode("ascii"),
        hashlib.sha256
    ).hexdigest()

    return f"{encoded_payload}.{signature}"


def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a signed session token. Returns payload dict or None if invalid/expired."""
    try:
        if not token or "." not in token:
            return None
        encoded_payload, signature = token.split(".", 1)

        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"),
            encoded_payload.encode("ascii"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_sig):
            return None

        # Add padding back if necessary
        padding = "=" * (4 - (len(encoded_payload) % 4)) if len(encoded_payload) % 4 else ""
        raw_json = base64.urlsafe_b64decode((encoded_payload + padding).encode("ascii")).decode("utf-8")
        payload = json.loads(raw_json)

        # Check expiration
        if "exp" in payload and time.time() > payload["exp"]:
            return None

        return payload
    except Exception:
        return None
