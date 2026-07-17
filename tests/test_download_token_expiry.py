"""
Regression coverage for audit Medium #24: create_download_token() never set
an exp claim despite JWT_DOWNLOAD_EXPIRE_MINUTES=10 being configured and
echoed to the client as expires_in — signed download URLs were valid
forever. It now actually expires, while still allowing more than one
fetch within that window (the single-use gate was deliberately removed
earlier to stop legitimate retries on a stalled download from being
locked out — this must not silently come back).
"""
import pytest
from datetime import timedelta
from unittest.mock import patch

from backend.utils.security import create_download_token, verify_token
from backend.config import get_settings

settings = get_settings()


def test_download_token_has_exp_claim_matching_config():
    token = create_download_token("user123", "product456")
    payload = verify_token(token)
    assert payload is not None
    assert "exp" in payload
    assert "iat" in payload
    assert payload["exp"] - payload["iat"] == settings.JWT_DOWNLOAD_EXPIRE_MINUTES * 60


def test_expired_download_token_is_rejected():
    with patch("backend.utils.security.timedelta", lambda **kw: timedelta(hours=-1)):
        token = create_download_token("user123", "product456")
    payload = verify_token(token)
    assert payload is None


def test_unexpired_download_token_can_be_verified_more_than_once():
    """The single-use lockout was deliberately removed (see routes/library.py
    download_file's comment) — a token must survive being checked twice
    within its valid window, not just once."""
    token = create_download_token("user123", "product456")
    first = verify_token(token)
    second = verify_token(token)
    assert first is not None
    assert second is not None
    assert first["jti"] == second["jti"]


@pytest.mark.asyncio
async def test_download_file_route_shows_expired_page_for_expired_token(client):
    with patch("backend.utils.security.timedelta", lambda **kw: timedelta(hours=-1)):
        expired_token = create_download_token("user123", "product456")

    res = await client.get(f"/api/library/file/{expired_token}")
    assert res.status_code == 403
    assert "expired" in res.text.lower() or "invalid" in res.text.lower()
