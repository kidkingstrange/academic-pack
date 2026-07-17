"""
Regression coverage for audit Medium #25: slowapi was a pinned dependency
but never actually wired into the app — login, checkout, and registration
endpoints had no brute-force/abuse throttling at all. Uses its own scratch
IP address per test (via X-Forwarded-For handling isn't configured here,
so slowapi keys purely on the test client's fixed pseudo-IP) — run this
file in isolation from the rest of the suite if adding new tests that also
hit these same routes, since slowapi's in-memory limiter state is global
to the process, not reset per test.
"""
import pytest

from backend.utils.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.reset()
    yield
    limiter.reset()


@pytest.mark.asyncio
async def test_admin_login_gets_rate_limited_after_repeated_attempts(client, test_db):
    for _ in range(10):
        res = await client.post("/api/admin/login", json={"email": "x@example.com", "password": "wrongpass"})
        assert res.status_code == 401

    res = await client.post("/api/admin/login", json={"email": "x@example.com", "password": "wrongpass"})
    assert res.status_code == 429


@pytest.mark.asyncio
async def test_sales_register_gets_rate_limited_after_repeated_attempts(client, test_db):
    for i in range(5):
        res = await client.post("/api/sales/register", json={
            "name": f"Rep {i}", "email": f"rep{i}@example.com", "password": "hunter22",
        })
        assert res.status_code == 200

    res = await client.post("/api/sales/register", json={
        "name": "One Too Many", "email": "toomany@example.com", "password": "hunter22",
    })
    assert res.status_code == 429


@pytest.mark.asyncio
async def test_payment_verify_allows_realistic_polling_volume(client, test_db):
    """checkout.js polls /verify every 5s for the first 3 minutes — up to
    ~12/minute in the worst case. The limit must not punish that."""
    for _ in range(15):
        res = await client.post("/api/payments/verify", json={
            "reference": "ACP-DOESNOTEXIST", "email": "x@example.com", "name": "X",
        })
        assert res.status_code != 429
