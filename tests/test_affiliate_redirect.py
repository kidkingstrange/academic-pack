"""
Tests for affiliate referral redirect (/r/{code}) and page routing.
"""
import pytest

@pytest.mark.asyncio
async def test_affiliate_redirect_valid_code(client, test_db):
    await test_db.affiliates.insert_one({
        "code": "TESTCODE",
        "name": "Test Affiliate",
        "email": "affiliate@example.com",
        "active": True,
    })

    res = await client.get("/r/TESTCODE", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "/academic-comeback-package?ref=TESTCODE&price=5000"

    click = await test_db.referral_clicks.find_one({"affiliate_code": "TESTCODE"})
    assert click is not None


@pytest.mark.asyncio
async def test_affiliate_redirect_invalid_code(client, test_db):
    res = await client.get("/r/UNKNOWNCODE", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "/academic-comeback-package"


@pytest.mark.asyncio
async def test_academic_comeback_package_route(client):
    res = await client.get("/academic-comeback-package")
    assert res.status_code == 200
    assert "Academic Comeback Package" in res.text
