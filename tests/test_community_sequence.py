"""
Regression coverage for audit High #12 (product decision): free WhatsApp
community joiners used to get enrolled in the same 52-email paid curriculum
as actual paying customers. They now get a short standalone welcome/value
sequence, and are correctly upgraded to the full curriculum if they later
convert to a paying customer (instead of being stuck on the short sequence
forever, which the naive fix would have caused).
"""
import asyncio
import pytest
from unittest.mock import AsyncMock

from backend.workers.email_scheduler import EMAIL_SEQUENCE, COMMUNITY_EMAIL_SEQUENCE
from backend.services.payment_completion import complete_payment


@pytest.mark.asyncio
async def test_community_join_queues_short_sequence_not_full_curriculum(client, test_db):
    res = await client.post("/api/community/join", json={"email": "freejoiner@example.com"})
    assert res.status_code == 200
    await asyncio.sleep(0.1)  # let the fire-and-forget enqueue task finish

    sub = await test_db.subscribers.find_one({"email": "freejoiner@example.com"})
    assert sub is not None
    assert "community" in sub["tags"]
    assert "buyer" not in sub.get("tags", [])

    queued = await test_db.email_queue.find({"subscriber_id": sub["_id"], "kind": "sequence"}).to_list(100)
    assert len(queued) == len(COMMUNITY_EMAIL_SEQUENCE)
    assert len(queued) < len(EMAIL_SEQUENCE)
    queued_templates = {q["template"] for q in queued}
    community_templates = {t for _, _, t in COMMUNITY_EMAIL_SEQUENCE}
    assert queued_templates == community_templates


@pytest.mark.asyncio
async def test_community_joiner_upgraded_to_full_curriculum_on_purchase(client, test_db, monkeypatch):
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock())

    res = await client.post("/api/community/join", json={"email": "laterbuyer@example.com"})
    assert res.status_code == 200
    await asyncio.sleep(0.1)  # let the fire-and-forget enqueue task finish
    sub_before = await test_db.subscribers.find_one({"email": "laterbuyer@example.com"})
    short_seq_count = await test_db.email_queue.count_documents(
        {"subscriber_id": sub_before["_id"], "kind": "sequence"}
    )
    assert short_seq_count == len(COMMUNITY_EMAIL_SEQUENCE)

    await complete_payment(
        test_db, reference="ACP-UPGRADE-001", email="laterbuyer@example.com", name="Later Buyer",
        amount=2000, charge_id="chg_1", gateway_response={}, completed_via="webhook",
    )

    sub_after = await test_db.subscribers.find_one({"email": "laterbuyer@example.com"})
    assert "buyer" in sub_after["tags"]
    # Still the same subscriber record — not duplicated.
    assert sub_after["_id"] == sub_before["_id"]

    # The leftover pending short-sequence emails must be skipped, not sent
    # alongside the new full sequence.
    skipped = await test_db.email_queue.count_documents(
        {"subscriber_id": sub_after["_id"], "kind": "sequence", "status": "skipped"}
    )
    assert skipped == len(COMMUNITY_EMAIL_SEQUENCE)

    full_seq_pending = await test_db.email_queue.count_documents(
        {"subscriber_id": sub_after["_id"], "kind": "sequence", "status": "pending"}
    )
    assert full_seq_pending == len(EMAIL_SEQUENCE)


@pytest.mark.asyncio
async def test_new_paying_customer_still_gets_full_curriculum(test_db, monkeypatch):
    monkeypatch.setattr("backend.services.payment_completion.process_email_queue", AsyncMock())

    await complete_payment(
        test_db, reference="ACP-DIRECT-001", email="directbuyer@example.com", name="Direct Buyer",
        amount=2000, charge_id="chg_2", gateway_response={}, completed_via="webhook",
    )

    sub = await test_db.subscribers.find_one({"email": "directbuyer@example.com"})
    assert "buyer" in sub["tags"]
    full_seq_count = await test_db.email_queue.count_documents(
        {"subscriber_id": sub["_id"], "kind": "sequence"}
    )
    assert full_seq_count == len(EMAIL_SEQUENCE)
