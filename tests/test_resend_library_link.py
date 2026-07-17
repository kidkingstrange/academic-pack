"""
Regression coverage for audit High #17: there was no self-service way for a
customer whose access link/localStorage was lost to recover it.
"""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_resend_link_queues_welcome_email_for_real_customer(client, test_db, monkeypatch):
    monkeypatch.setattr("backend.routes.library.process_email_queue", AsyncMock())

    user_id = (await test_db.users.insert_one({
        "email": "existing@example.com", "name": "Existing Customer",
        "role": "customer", "is_active": True,
        "purchased_products": ["all"], "library_access_token": "real-token-123",
    })).inserted_id

    res = await client.post("/api/library/resend-link", json={"email": "EXISTING@example.com"})
    assert res.status_code == 200
    assert res.json()["success"] is True

    queued = await test_db.email_queue.find_one({"user_id": user_id, "kind": "welcome"})
    assert queued is not None
    assert queued["access_token"] == "real-token-123"
    assert queued["status"] == "pending"


@pytest.mark.asyncio
async def test_resend_link_does_not_reveal_whether_email_exists(client, test_db, monkeypatch):
    monkeypatch.setattr("backend.routes.library.process_email_queue", AsyncMock())

    res_unknown = await client.post("/api/library/resend-link", json={"email": "nobody@example.com"})
    res_known_setup = await test_db.users.insert_one({
        "email": "known@example.com", "name": "Known", "role": "customer",
        "is_active": True, "purchased_products": ["all"], "library_access_token": "tok",
    })
    res_known = await client.post("/api/library/resend-link", json={"email": "known@example.com"})

    assert res_unknown.status_code == res_known.status_code == 200
    assert res_unknown.json()["message"] == res_known.json()["message"]

    queued_for_unknown = await test_db.email_queue.count_documents({"email": "nobody@example.com"})
    assert queued_for_unknown == 0
