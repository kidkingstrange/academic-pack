"""
Tests for affiliate authentication, account activation, password reset,
and dashboard session verification.
"""
import pytest
from bson import ObjectId
from datetime import datetime, timezone, timedelta

from backend.utils.security import hash_password, create_access_token
from backend.middleware.auth import _account_still_active
from backend.workers.email_scheduler import process_email_queue


@pytest.mark.asyncio
async def test_affiliate_account_active_status_check(test_db):
    """
    Affiliates with active=True or missing active field must be accepted.
    Only explicit active=False must be rejected.
    """
    # 1. Active affiliate
    aff1_id = (await test_db.affiliates.insert_one({
        "name": "Aff Active",
        "email": "active@example.com",
        "code": "ACT123",
        "active": True,
    })).inserted_id
    assert await _account_still_active(test_db, str(aff1_id), "affiliate") is True

    # 2. Legacy affiliate (no active field)
    aff2_id = (await test_db.affiliates.insert_one({
        "name": "Aff Legacy",
        "email": "legacy@example.com",
        "code": "LEG123",
    })).inserted_id
    assert await _account_still_active(test_db, str(aff2_id), "affiliate") is True

    # 3. Suspended affiliate (active=False)
    aff3_id = (await test_db.affiliates.insert_one({
        "name": "Aff Inactive",
        "email": "inactive@example.com",
        "code": "INACT123",
        "active": False,
    })).inserted_id
    assert await _account_still_active(test_db, str(aff3_id), "affiliate") is False


@pytest.mark.asyncio
async def test_affiliate_self_registration_with_password(client, test_db):
    """
    Registering with a password establishes credentials immediately,
    sets account_activated=True, and returns an access_token.
    """
    payload = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "password": "SecurePassword123!",
        "bank_name": "Access Bank",
        "bank_code": "044",
        "account_number": "0123456789",
        "account_name": "Ada Lovelace",
    }
    res = await client.post("/api/affiliates/register", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "code" in data
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify affiliate record in DB
    aff = await test_db.affiliates.find_one({"email": "ada@example.com"})
    assert aff is not None
    assert aff["account_activated"] is True
    assert aff["password_hash"] is not None

    # Test immediate login with established password
    login_res = await client.post("/api/affiliate/auth/login", json={
        "email": "ada@example.com",
        "password": "SecurePassword123!",
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["code"] == aff["code"]


@pytest.mark.asyncio
async def test_unactivated_affiliate_login_guidance(client, test_db):
    """
    If an affiliate exists without a password (legacy / unactivated),
    login returns HTTP 403 with X-Needs-Activation header.
    """
    await test_db.affiliates.insert_one({
        "name": "Unactivated User",
        "email": "unactivated@example.com",
        "code": "UNACT1",
        "account_activated": False,
        "password_hash": None,
        "active": True,
    })

    res = await client.post("/api/affiliate/auth/login", json={
        "email": "unactivated@example.com",
        "password": "anyPassword123",
    })
    assert res.status_code == 403
    assert "activate your account" in res.json()["detail"].lower()
    assert res.headers.get("x-needs-activation") == "true"


@pytest.mark.asyncio
async def test_account_activation_flow(client, test_db):
    """
    Full activation lifecycle:
    1. Request activation link.
    2. Verify token.
    3. Confirm password.
    4. Auto-login and access dashboard.
    5. Token cannot be reused.
    """
    aff_id = (await test_db.affiliates.insert_one({
        "name": "Charles Babbage",
        "email": "charles@example.com",
        "code": "BABBAGE1",
        "dashboard_token": "dash_babbage_123",
        "account_activated": False,
        "password_hash": None,
        "active": True,
    })).inserted_id

    # 1. Request activation link
    req_res = await client.post("/api/affiliate/auth/activate/request", json={
        "email": "Charles@Example.com"  # Test case-insensitivity
    })
    assert req_res.status_code == 200
    req_data = req_res.json()
    assert req_data["status"] == "success"
    activation_link = req_data.get("activation_link")
    assert activation_link is not None
    token = activation_link.split("token=")[1]

    # Verify email queue item
    email_item = await test_db.email_queue.find_one({"kind": "affiliate_activation"})
    assert email_item is not None
    assert email_item["email"] == "charles@example.com"

    # 2. Verify token
    verify_res = await client.get(f"/api/affiliate/auth/activate/verify?token={token}")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["valid"] is True
    assert v_data["email"] == "charles@example.com"

    # 3. Confirm password
    confirm_res = await client.post("/api/affiliate/auth/activate/confirm", json={
        "token": token,
        "password": "NewSecretPassword123!",
    })
    assert confirm_res.status_code == 200
    c_data = confirm_res.json()
    assert c_data["status"] == "success"
    assert "access_token" in c_data
    assert c_data["dashboard_token"] == "dash_babbage_123"

    # Check database state
    updated_aff = await test_db.affiliates.find_one({"_id": aff_id})
    assert updated_aff["account_activated"] is True
    assert updated_aff.get("activation_token_hash") is None

    # 4. Token cannot be reused
    reuse_res = await client.get(f"/api/affiliate/auth/activate/verify?token={token}")
    assert reuse_res.status_code == 400

    # 5. Access /api/affiliate/me with the issued access_token
    dash_res = await client.get(
        "/api/affiliate/me",
        headers={"Authorization": f"Bearer {c_data['access_token']}"}
    )
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["code"] == "BABBAGE1"


@pytest.mark.asyncio
async def test_password_reset_flow(client, test_db):
    """
    Forgot password lifecycle:
    1. Request reset link.
    2. Verify reset token.
    3. Confirm new password.
    4. Auto-login token returned.
    """
    await test_db.affiliates.insert_one({
        "name": "Grace Hopper",
        "email": "grace@example.com",
        "code": "HOPPER1",
        "dashboard_token": "dash_hopper_123",
        "account_activated": True,
        "password_hash": hash_password("OldPassword123!"),
        "active": True,
    })

    # 1. Request reset
    req_res = await client.post("/api/affiliate/auth/forgot-password/request", json={
        "email": "grace@example.com"
    })
    assert req_res.status_code == 200
    reset_link = req_res.json().get("reset_link")
    assert reset_link is not None
    token = reset_link.split("token=")[1]

    # 2. Verify token
    verify_res = await client.get(f"/api/affiliate/auth/forgot-password/verify?token={token}")
    assert verify_res.status_code == 200
    assert verify_res.json()["email"] == "grace@example.com"

    # 3. Confirm password
    confirm_res = await client.post("/api/affiliate/auth/forgot-password/confirm", json={
        "token": token,
        "password": "BrandNewPassword123!",
    })
    assert confirm_res.status_code == 200
    c_data = confirm_res.json()
    assert "access_token" in c_data
    assert c_data["dashboard_token"] == "dash_hopper_123"

    # 4. Login with new password
    login_res = await client.post("/api/affiliate/auth/login", json={
        "email": "grace@example.com",
        "password": "BrandNewPassword123!",
    })
    assert login_res.status_code == 200


@pytest.mark.asyncio
async def test_email_scheduler_transactional_no_subscriber_id(test_db):
    """
    Transactional emails (affiliate_activation, affiliate_password_reset, etc.)
    must not fail with KeyError: 'subscriber_id' in process_email_queue.
    """
    now = datetime.now(timezone.utc)
    # Insert pending transactional affiliate email without subscriber_id
    await test_db.email_queue.insert_one({
        "kind": "affiliate_activation",
        "email": "test@example.com",
        "name": "Test User",
        "code": "TEST1",
        "activation_link": "http://localhost:8080/affiliate/activate?token=abc",
        "scheduled_at": now - timedelta(minutes=1),
        "status": "pending",
        "retry_count": 0,
        "sent_at": None,
        "error": None,
    })

    # Process queue — must not raise KeyError: 'subscriber_id'
    await process_email_queue()

    # The item should not be stuck with status='retry' due to KeyError
    item = await test_db.email_queue.find_one({"email": "test@example.com"})
    assert item is not None
    if item.get("error"):
        assert "subscriber_id" not in item["error"]


@pytest.mark.asyncio
async def test_admin_analytics_affiliates_activation_status_fields(client, test_db):
    """
    GET /api/admin/analytics/affiliates must return activation_status,
    account_activated, and last_login for every affiliate.
    """
    admin_token = create_access_token({"sub": "admin", "email": "admin@example.com", "role": "admin"})

    now = datetime.now(timezone.utc)
    # 1. Activated affiliate
    await test_db.affiliates.insert_one({
        "name": "Activated User",
        "email": "act_user@example.com",
        "code": "ACTU1",
        "password_hash": hash_password("Password123!"),
        "account_activated": True,
        "active": True,
        "created_at": now,
        "last_login": now,
    })
    # 2. Pending activation affiliate
    await test_db.affiliates.insert_one({
        "name": "Pending User",
        "email": "pen_user@example.com",
        "code": "PENU1",
        "activation_token_hash": "dummyhash",
        "activation_token_expires_at": now + timedelta(hours=1),
        "account_activated": False,
        "active": True,
        "created_at": now,
    })
    # 3. Not activated affiliate
    await test_db.affiliates.insert_one({
        "name": "Unset User",
        "email": "unset_user@example.com",
        "code": "UNSET1",
        "account_activated": False,
        "active": True,
        "created_at": now,
    })

    res = await client.get("/api/admin/analytics/affiliates", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    affiliates_map = {a["code"]: a for a in data.get("affiliates", [])}

    assert "ACTU1" in affiliates_map
    assert affiliates_map["ACTU1"]["activation_status"] == "active"
    assert affiliates_map["ACTU1"]["account_activated"] is True
    assert affiliates_map["ACTU1"]["last_login"] is not None

    assert "PENU1" in affiliates_map
    assert affiliates_map["PENU1"]["activation_status"] == "pending"
    assert affiliates_map["PENU1"]["account_activated"] is False

    assert "UNSET1" in affiliates_map
    assert affiliates_map["UNSET1"]["activation_status"] == "not_activated"
    assert affiliates_map["UNSET1"]["account_activated"] is False


@pytest.mark.asyncio
async def test_admin_create_affiliate_bank_details_and_activation(client, test_db):
    """
    POST /api/admin/affiliates must preserve bank details and automatically
    queue an affiliate_activation email with an activation link.
    """
    admin_token = create_access_token({"sub": "admin", "email": "admin@example.com", "role": "admin"})

    res = await client.post(
        "/api/admin/affiliates",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Admin Onboarded",
            "email": "onboarded@example.com",
            "code": "ONBOARD1",
            "commission_percent": 45.0,
            "bank_name": "Kuda Bank",
            "bank_code": "50211",
            "account_number": "1122334455",
            "account_name": "Onboarded Partner",
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == "ONBOARD1"
    assert data["bank_name"] == "Kuda Bank"
    assert data["account_number"] == "1122334455"
    assert "activation_link" in data

    # Verify document in DB
    doc = await test_db.affiliates.find_one({"code": "ONBOARD1"})
    assert doc is not None
    assert doc["bank_name"] == "Kuda Bank"
    assert doc["bank_code"] == "50211"
    assert doc["account_number"] == "1122334455"
    assert doc["account_name"] == "Onboarded Partner"
    assert doc["activation_token_hash"] is not None

    # Verify activation email queued
    email_doc = await test_db.email_queue.find_one({"email": "onboarded@example.com", "kind": "affiliate_activation"})
    assert email_doc is not None
    assert email_doc["activation_link"] == data["activation_link"]


@pytest.mark.asyncio
async def test_admin_toggle_affiliate_status_and_login_blocking(client, test_db):
    """
    PATCH /api/admin/affiliates/{id}/status toggles active state.
    When active=False, affiliate login and click tracking must be rejected.
    """
    admin_token = create_access_token({"sub": "admin", "email": "admin@example.com", "role": "admin"})

    now = datetime.now(timezone.utc)
    aff_id = (await test_db.affiliates.insert_one({
        "name": "Toggle Partner",
        "email": "toggle@example.com",
        "code": "TOGGLE1",
        "password_hash": hash_password("StrongPass123!"),
        "account_activated": True,
        "active": True,
        "created_at": now,
    })).inserted_id

    # 1. Login works when active
    login1 = await client.post("/api/affiliate/auth/login", json={
        "email": "toggle@example.com",
        "password": "StrongPass123!",
    })
    assert login1.status_code == 200

    # 2. Admin suspends affiliate
    status_res = await client.patch(
        f"/api/admin/affiliates/{str(aff_id)}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"active": False}
    )
    assert status_res.status_code == 200
    assert status_res.json()["active"] is False

    # 3. Login is blocked when suspended
    login2 = await client.post("/api/affiliate/auth/login", json={
        "email": "toggle@example.com",
        "password": "StrongPass123!",
    })
    assert login2.status_code == 401
    assert "suspended" in login2.json()["detail"].lower()

    # 4. Admin reactivates affiliate
    reactivate_res = await client.patch(
        f"/api/admin/affiliates/{str(aff_id)}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"active": True}
    )
    assert reactivate_res.status_code == 200
    assert reactivate_res.json()["active"] is True

    # 5. Login succeeds again
    login3 = await client.post("/api/affiliate/auth/login", json={
        "email": "toggle@example.com",
        "password": "StrongPass123!",
    })
    assert login3.status_code == 200


@pytest.mark.asyncio
async def test_admin_update_affiliate_details(client, test_db):
    """
    PATCH /api/admin/affiliates/{id}/details updates partner profile and bank info.
    """
    admin_token = create_access_token({"sub": "admin", "email": "admin@example.com", "role": "admin"})

    now = datetime.now(timezone.utc)
    aff_id = (await test_db.affiliates.insert_one({
        "name": "Old Name",
        "email": "oldemail@example.com",
        "code": "OLDNAME1",
        "commission_percent": 30.0,
        "active": True,
        "created_at": now,
    })).inserted_id

    res = await client.patch(
        f"/api/admin/affiliates/{str(aff_id)}/details",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "New Name",
            "email": "newemail@example.com",
            "bank_name": "Access Bank",
            "account_number": "0123456789",
            "account_name": "New Name Account",
            "commission_percent": 40.0,
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["affiliate"]["name"] == "New Name"
    assert data["affiliate"]["email"] == "newemail@example.com"
    assert data["affiliate"]["bank_name"] == "Access Bank"
    assert data["affiliate"]["account_number"] == "0123456789"
    assert data["affiliate"]["commission_percent"] == 40.0


@pytest.mark.asyncio
async def test_bank_code_auto_resolution_in_dashboard(client, test_db):
    """
    When an affiliate updates bank details with a known bank name like 'GTBank' or 'Kuda',
    the system auto-resolves the bank code even if bank_code is omitted.
    """
    now = datetime.now(timezone.utc)
    aff_id = (await test_db.affiliates.insert_one({
        "name": "Bank Test",
        "email": "banktest@example.com",
        "code": "BANKT1",
        "dashboard_token": "token_bank_test_123",
        "active": True,
        "created_at": now,
    })).inserted_id

    res = await client.post(
        "/api/affiliate/bank-details?token=token_bank_test_123",
        json={
            "bank_name": "Guaranty Trust Bank (GTBank)",
            "account_number": "0123456789",
            "account_name": "Bank Test Holder",
        }
    )
    assert res.status_code == 200
    doc = await test_db.affiliates.find_one({"_id": aff_id})
    assert doc is not None
    # 058 is the canonical GTBank code in Nigerian NUBAN
    assert doc.get("bank_code") == "058"

