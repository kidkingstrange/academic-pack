"""
Regression coverage for the auth-middleware gap (audit High #11): a valid
signed JWT used to be trusted at face value with no database check, so a
deleted or demoted account could keep acting on a still-valid token until
it naturally expired (up to JWT_EXPIRE_DAYS).
"""
import pytest

from backend.middleware.auth import _account_still_active
from backend.utils.security import create_access_token


@pytest.mark.asyncio
async def test_env_admin_login_always_active(test_db):
    assert await _account_still_active(test_db, "admin", "admin") is True


@pytest.mark.asyncio
async def test_customer_account_deleted_is_rejected(test_db):
    user_id = (await test_db.users.insert_one({
        "email": "deleteme@example.com", "name": "Delete Me",
        "role": "customer", "is_active": True,
        "purchased_products": ["all"], "library_access_token": "tok",
    })).inserted_id
    assert await _account_still_active(test_db, str(user_id), "customer") is True

    await test_db.users.delete_one({"_id": user_id})
    assert await _account_still_active(test_db, str(user_id), "customer") is False


@pytest.mark.asyncio
async def test_admin_route_rejects_deleted_admin_accounts_token(client, test_db):
    """End-to-end HTTP check: a real admin route (require_admin -> Depends
    on get_current_user) must reject a structurally-valid JWT once the
    admin_accounts row it points at is gone."""
    admin_id = (await test_db.admin_accounts.insert_one({
        "email": "gone-admin@example.com", "password_hash": "x",
    })).inserted_id
    token = create_access_token({"sub": str(admin_id), "email": "gone-admin@example.com", "role": "admin"})

    res = await client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

    await test_db.admin_accounts.delete_one({"_id": admin_id})
    res = await client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_sales_rep_token_rejected_after_suspension(test_db):
    rep_id = (await test_db.sales_reps.insert_one({
        "name": "Rep", "email": "rep@example.com", "password_hash": "x", "active": True,
    })).inserted_id
    assert await _account_still_active(test_db, str(rep_id), "sales_rep") is True

    await test_db.sales_reps.update_one({"_id": rep_id}, {"$set": {"active": False}})
    assert await _account_still_active(test_db, str(rep_id), "sales_rep") is False


@pytest.mark.asyncio
async def test_admin_account_token_rejected_after_deletion(test_db):
    admin_id = (await test_db.admin_accounts.insert_one({
        "email": "teamadmin@example.com", "password_hash": "x",
    })).inserted_id
    assert await _account_still_active(test_db, str(admin_id), "admin") is True

    await test_db.admin_accounts.delete_one({"_id": admin_id})
    assert await _account_still_active(test_db, str(admin_id), "admin") is False


@pytest.mark.asyncio
async def test_malformed_user_id_is_rejected_not_crashed(test_db):
    assert await _account_still_active(test_db, "not-a-valid-object-id", "customer") is False
