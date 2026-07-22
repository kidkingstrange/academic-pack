"""
Coverage for sales rep self-registration: sales reps register and are immediately active.
"""
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_self_registered_rep_can_login_immediately(client, test_db, monkeypatch):
    monkeypatch.setattr("backend.routes.sales.send_email", AsyncMock(return_value=(True, None)))

    res = await client.post("/api/sales/register", json={
        "name": "New Rep", "email": "newrep@example.com", "password": "hunter22",
    })
    assert res.status_code == 200

    rep = await test_db.sales_reps.find_one({"email": "newrep@example.com"})
    assert rep is not None
    assert rep["active"] is True

    login_res = await client.post("/api/sales/login", json={
        "email": "newrep@example.com", "password": "hunter22",
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

