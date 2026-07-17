"""
Regression coverage for audit Low #48: the public self-registration form
actively collects and verifies bank details (live account-name resolution,
blocks submit on an invalid account number) but the backend schema made
them optional — an inconsistency between what the UI enforces and what the
API actually accepts. AffiliateRegisterRequest now requires them to match
the form's real, deliberate UX. AffiliateCreateRequest (the admin-created
path) is untouched — an admin may not have the affiliate's bank details on
hand yet, so optional stays correct there.
"""
import pytest


@pytest.mark.asyncio
async def test_public_registration_rejects_missing_bank_details(client, test_db):
    res = await client.post("/api/affiliates/register", json={
        "name": "New Affiliate", "email": "newaff@example.com",
    })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_public_registration_succeeds_with_full_bank_details(client, test_db):
    res = await client.post("/api/affiliates/register", json={
        "name": "New Affiliate", "email": "newaff2@example.com",
        "bank_name": "GTBank", "account_number": "1234567890", "account_name": "New Affiliate",
    })
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_admin_created_affiliate_still_allows_missing_bank_details(client, test_db):
    from backend.utils.security import create_access_token
    admin_id = (await test_db.admin_accounts.insert_one({
        "email": "bankcheckadmin@example.com", "password_hash": "x",
    })).inserted_id
    token = create_access_token({"sub": str(admin_id), "email": "bankcheckadmin@example.com", "role": "admin"})

    res = await client.post(
        "/api/admin/affiliates",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Admin Created Affiliate", "email": "admincreated@example.com"},
    )
    assert res.status_code == 200
