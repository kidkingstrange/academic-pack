"""
Regression coverage for audit High #13: POST /api/sales/register used to
create a fully active, immediately-usable sales-rep account with no
approval step. It now creates the account inactive — same as any suspended
rep in the admin's Team Members list — until an admin explicitly activates it.
"""
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_self_registered_rep_is_inactive_and_cannot_login(client, test_db, monkeypatch):
    monkeypatch.setattr("backend.routes.sales.send_email", AsyncMock(return_value=(True, None)))

    res = await client.post("/api/sales/register", json={
        "name": "New Rep", "email": "newrep@example.com", "password": "hunter22",
    })
    assert res.status_code == 200

    rep = await test_db.sales_reps.find_one({"email": "newrep@example.com"})
    assert rep is not None
    assert rep["active"] is False

    login_res = await client.post("/api/sales/login", json={
        "email": "newrep@example.com", "password": "hunter22",
    })
    assert login_res.status_code == 401


@pytest.mark.asyncio
async def test_admin_activation_lets_rep_login(client, test_db, monkeypatch):
    monkeypatch.setattr("backend.routes.sales.send_email", AsyncMock(return_value=(True, None)))

    await client.post("/api/sales/register", json={
        "name": "Approve Me", "email": "approveme@example.com", "password": "hunter22",
    })
    rep = await test_db.sales_reps.find_one({"email": "approveme@example.com"})

    # Simulates the admin clicking "Activate" in the Team Members tab.
    await test_db.sales_reps.update_one({"_id": rep["_id"]}, {"$set": {"active": True}})

    login_res = await client.post("/api/sales/login", json={
        "email": "approveme@example.com", "password": "hunter22",
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()
