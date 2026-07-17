import pytest
from starlette.requests import Request
from backend.utils.rate_limit import get_real_client_ip, _is_trusted_proxy


def test_is_trusted_proxy():
    assert _is_trusted_proxy("127.0.0.1") is True
    assert _is_trusted_proxy("10.0.1.5") is True
    assert _is_trusted_proxy("8.8.8.8") is False


def test_get_real_client_ip_behind_trusted_proxy():
    # Direct request from untrusted external IP attempting to spoof header
    scope_untrusted = {
        "type": "http",
        "client": ("198.51.100.1", 50000),
        "headers": [(b"x-forwarded-for", b"1.1.1.1")],
    }
    req_untrusted = Request(scope_untrusted)
    assert get_real_client_ip(req_untrusted) == "198.51.100.1"

    # Request proxied through local trusted proxy (127.0.0.1)
    scope_trusted = {
        "type": "http",
        "client": ("127.0.0.1", 50000),
        "headers": [
            (b"x-forwarded-for", b"203.0.113.195, 127.0.0.1"),
            (b"x-real-ip", b"203.0.113.195"),
        ],
    }
    req_trusted = Request(scope_trusted)
    assert get_real_client_ip(req_trusted) == "203.0.113.195"
