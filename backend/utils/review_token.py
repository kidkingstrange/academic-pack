"""
Signed review token generator and verifier.
Creates unguessable, tamper-proof, time-stamped tokens for review links.
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from ..config import get_settings

settings = get_settings()


def _get_secret() -> bytes:
    key = (settings.APP_SECRET_KEY or "dev-secret-key-review-salt").encode("utf-8")
    return key


def generate_review_token(reference: str, email: str, name: str) -> str:
    """
    Generate a signed, URL-safe review token.
    Payload: {"ref": reference, "email": email.lower(), "name": name, "iat": int(time.time())}
    """
    payload = {
        "ref": reference,
        "email": email.strip().lower(),
        "name": name.strip(),
        "iat": int(time.time()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")

    signature = hmac.new(_get_secret(), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{signature}"


def verify_review_token(token: str) -> Optional[dict]:
    """
    Verify signature and decode payload. Returns payload dict or None if invalid.
    """
    if not token or "." not in token:
        return None

    parts = token.strip().split(".")
    if len(parts) != 2:
        return None

    b64_payload, signature = parts
    expected_sig = hmac.new(_get_secret(), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        return None

    # Pad base64 if needed
    rem = len(b64_payload) % 4
    padded = b64_payload + ("=" * (4 - rem) if rem else "")

    try:
        raw_json = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        payload = json.loads(raw_json)
        if not isinstance(payload, dict) or "ref" not in payload or "email" not in payload:
            return None
        return payload
    except Exception:
        return None


def hash_review_token(token: str) -> str:
    """
    Returns a deterministic SHA256 hex digest of the token for database indexing/idempotency.
    """
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
