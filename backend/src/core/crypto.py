"""Field-level symmetric encryption for tamper-evident audit payloads.

Implements a standard HMAC-SHA256 based keystream cipher (HMAC used as a PRF in
counter mode). Used to encrypt audit `detail` payloads at rest so they satisfy the
"encrypted retention >= 180 days" constraint of opchub_legal_compliance_spec §80.
"""
import base64
import hashlib
import hmac
import os

from src.core.config import settings

_NONCE_LEN = 16
_DEFAULT_SECRET = "opchub-audit-field-encryption-secret-2026"


def _secret() -> bytes:
    secret = getattr(settings, "audit_secret", "") or os.getenv("OPCHUB_AUDIT_SECRET", "")
    if not secret:
        secret = os.getenv("OPCHUB_SECRET_KEY", _DEFAULT_SECRET)
    return secret.encode("utf-8")


def _keystream(length: int, nonce: bytes) -> bytes:
    """Deterministic HMAC-SHA256 keystream in counter mode."""
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hmac.new(_secret(), nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return bytes(out[:length])


def encrypt_text(plaintext: str) -> str:
    """Encrypt a UTF-8 string. Output: urlsafe-base64(nonce || ciphertext)."""
    data = (plaintext or "").encode("utf-8")
    nonce = os.urandom(_NONCE_LEN)
    ks = _keystream(len(data), nonce)
    ciphertext = bytes(a ^ b for a, b in zip(data, ks))
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_text(token: str) -> str:
    """Decrypt a value produced by :func:`encrypt_text`. Returns "" on failure."""
    try:
        raw = base64.urlsafe_b64decode((token or "").encode("ascii"))
        nonce, ciphertext = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
        ks = _keystream(len(ciphertext), nonce)
        return bytes(a ^ b for a, b in zip(ciphertext, ks)).decode("utf-8")
    except Exception:
        return ""


def short_fingerprint(value: str) -> str:
    """Deterministic short fingerprint for integrity verification (not reversible)."""
    return "fp_" + hmac.new(_secret(), (value or "").encode("utf-8"), hashlib.sha256).hexdigest()[:16]
