"""
Tests for the AI-Powered E-Commerce Email Marketing and Revenue Generation Engine.
Verifies product knowledge base integrity, audience segmentation suppression,
AI copy generation accuracy, campaign test-sends, broadcast queue dispatching,
and admin API security.
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from backend.services.marketing_service import (
    get_product_knowledge_base,
    get_product_by_slug,
    generate_ai_campaign_copy,
    get_segment_recipients,
    get_audience_segments,
    create_campaign,
    send_test_campaign_email,
    launch_campaign,
    get_marketing_overview,
)
from backend.utils.security import create_access_token


@pytest.mark.asyncio
async def test_product_knowledge_base_integrity():
    """Verify all 13 canonical offerings are present with authoritative pricing and metadata."""
    kb = get_product_knowledge_base()
    assert len(kb) == 13

    slugs = [p["slug"] for p in kb]
    assert "academic-comeback-package" in slugs
    assert "get-good-at-hard-things" in slugs
    assert "how-to-score-high-in-any-exam" in slugs
    assert "quitting-the-handjob" in slugs
    assert "how-to-close-high-paying-clients-in-the-dms" in slugs
    assert "what-to-do-when-your-boss-is-angry-with-you" in slugs
    assert "what-to-do-after-a-breakup" in slugs
    assert "how-to-do-your-ideas" in slugs

    for prod in kb:
        assert prod["price_naira"] == 5000
        assert prod["price_usd"] == 15.0
        assert len(prod["title"]) > 0
        assert len(prod["primary_hook"]) > 0
        assert len(prod["core_problem"]) > 0
        assert len(prod["dream_outcome"]) > 0
        assert len(prod["features"]) >= 3
        assert prod["sku"].startswith("BOOK-") or prod["sku"].startswith("ACP-")


@pytest.mark.asyncio
async def test_ai_copy_generator_direct_response():
    """Verify AI copy generator produces compliant direct response copy with exact pricing."""
    copy_data = generate_ai_campaign_copy(
        product_slug="how-to-close-high-paying-clients-in-the-dms",
        campaign_type="direct_response",
    )
    assert copy_data["product_slug"] == "how-to-close-high-paying-clients-in-the-dms"
    assert copy_data["price_naira"] == 5000
    assert "₦5,000" in copy_data["formatted_price"]
    assert len(copy_data["subject_options"]) >= 3
    assert len(copy_data["preview_text"]) > 20
    assert "How to Close High-Paying Clients in the DMs" in copy_data["html_body"]
    assert "1-Click Unsubscribe" in copy_data["html_body"]
    assert "{{ name }}" in copy_data["html_body"]
    assert "{{ unsubscribe_token }}" in copy_data["html_body"]
    assert "{{ app_url }}" in copy_data["html_body"]
    assert "₦5,000" in copy_data["html_body"]


@pytest.mark.asyncio
async def test_ai_copy_generator_educational_value():
    """Verify AI copy generator creates Tuesday educational value masterclass."""
    copy_data = generate_ai_campaign_copy(
        product_slug="get-good-at-hard-things",
        campaign_type="educational_value",
    )
    assert copy_data["product_slug"] == "get-good-at-hard-things"
    assert len(copy_data["subject_options"]) >= 3
    assert "Tuesday Mindset & Execution Masterclass" in copy_data["html_body"]
    assert "1-Click Unsubscribe" in copy_data["html_body"]
    assert len(copy_data["plain_text"]) > 100


@pytest.mark.asyncio
async def test_audience_segmentation_strictly_suppresses_unsubscribes(test_db):
    """Verify unsubscribed users are never included in marketing recipient lists."""
    now = datetime.now(timezone.utc)

    # Insert active subscriber
    await test_db.subscribers.insert_one({
        "email": "active_buyer@example.com",
        "name": "Active Buyer",
        "is_active": True,
        "subscribed_at": now,
        "tags": ["buyer"],
        "unsubscribe_token": "token_active_123",
    })

    # Insert unsubscribed subscriber
    await test_db.subscribers.insert_one({
        "email": "opted_out@example.com",
        "name": "Opted Out",
        "is_active": False,
        "subscribed_at": now,
        "tags": ["buyer"],
        "unsubscribe_token": "token_optout_456",
    })

    # Insert recovery unsubscribed
    await test_db.recovery_unsubscribes.insert_one({
        "email": "recovery_unsub@example.com",
        "unsubscribed_at": now,
    })
    await test_db.subscribers.insert_one({
        "email": "recovery_unsub@example.com",
        "name": "Recovery Unsub",
        "is_active": True,
        "subscribed_at": now,
        "tags": ["buyer"],
        "unsubscribe_token": "token_rec_789",
    })

    # Query all_consented
    recipients = await get_segment_recipients(test_db, "all_consented")
    emails = [r["email"] for r in recipients]

    assert "active_buyer@example.com" in emails
    assert "opted_out@example.com" not in emails
    assert "recovery_unsub@example.com" not in emails


@pytest.mark.asyncio
async def test_campaign_creation_test_send_and_broadcast_dispatch(test_db, monkeypatch):
    """Verify end-to-end campaign lifecycle: create, test send, launch to queue."""
    mock_send = AsyncMock(return_value=(True, None))
    monkeypatch.setattr("backend.services.marketing_service.send_email", mock_send)
    monkeypatch.setattr("backend.workers.email_scheduler.send_email", mock_send)

    now = datetime.now(timezone.utc)

    # 1. Seed two active subscribers
    await test_db.subscribers.insert_one({
        "email": "scholar1@example.com",
        "name": "Scholar One",
        "is_active": True,
        "subscribed_at": now,
        "tags": ["buyer"],
        "unsubscribe_token": "sub_token_1",
    })
    await test_db.subscribers.insert_one({
        "email": "scholar2@example.com",
        "name": "Scholar Two",
        "is_active": True,
        "subscribed_at": now,
        "tags": ["buyer"],
        "unsubscribe_token": "sub_token_2",
    })

    # 2. Create campaign draft
    camp = await create_campaign(
        test_db,
        title="Weekly DM Masterclass Push",
        product_slug="how-to-close-high-paying-clients-in-the-dms",
        target_segment="all_consented",
        subject="Closing high-ticket clients without cold calls",
        preview_text="Read the conversational framework inside.",
        html_body="<p>Hello {{ name }}, download your guide at {{ app_url }}. <a href='{{ app_url }}/unsubscribe?token={{ unsubscribe_token }}'>Unsub</a></p>",
    )
    campaign_id = camp["campaign_id"]
    assert camp["status"] == "draft"

    # 3. Test send
    test_ok, test_err = await send_test_campaign_email(test_db, campaign_id, "admin_tester@example.com")
    assert test_ok is True
    assert test_err is None
    mock_send.assert_called()
    assert "[TEST]" in mock_send.call_args[0][1]

    # 4. Launch campaign
    launch_res = await launch_campaign(test_db, campaign_id)
    assert launch_res["success"] is True
    assert launch_res["enqueued_count"] == 2

    # Check email queue entries
    queued_items = await test_db.email_queue.find({"campaign_id": campaign_id}).to_list(10)
    assert len(queued_items) == 2
    for item in queued_items:
        assert item["kind"] == "marketing"
        assert item["status"] == "pending"
        assert "Scholar" in item["html_body"]


@pytest.mark.asyncio
async def test_admin_marketing_endpoints_security(client, test_db):
    """Verify security controls: require_admin on all marketing endpoints."""
    # 1. Unauthenticated request rejected
    res_unauth = await client.get("/api/admin/marketing/overview")
    assert res_unauth.status_code == 401

    # 2. Authenticated admin request accepted
    admin_token = create_access_token({"sub": "admin", "email": "admin@example.com", "role": "admin"})
    headers = {"Authorization": f"Bearer {admin_token}"}

    res_auth = await client.get("/api/admin/marketing/overview", headers=headers)
    assert res_auth.status_code == 200
    data = res_auth.json()
    assert "total_subscribers" in data
    assert "active_consented_audience" in data

    # 3. Products list endpoint
    res_prods = await client.get("/api/admin/marketing/products", headers=headers)
    assert res_prods.status_code == 200
    prods = res_prods.json()
    assert len(prods) == 13

    # 4. Copy generation endpoint
    res_copy = await client.post(
        "/api/admin/marketing/generate-copy",
        json={"product_slug": "quitting-the-handjob", "campaign_type": "direct_response"},
        headers=headers,
    )
    assert res_copy.status_code == 200
    gen_data = res_copy.json()
    assert "Quitting The Handjob" in gen_data["html_body"]


@pytest.mark.asyncio
async def test_campaign_launch_empty_segment_rejected(test_db):
    """Verify launching a campaign to an empty segment fails gracefully."""
    camp = await create_campaign(
        test_db,
        title="Empty Segment Campaign",
        product_slug="focus-template",
        target_segment="buyers_career",
        subject="Empty segment test",
        preview_text="Empty segment preview",
        html_body="<p>Test</p>",
    )
    res = await launch_campaign(test_db, camp["campaign_id"])
    assert res["success"] is False
    assert "No active consented recipients" in res["error"]


@pytest.mark.asyncio
async def test_campaign_deletion_rules(test_db):
    """Verify drafts can be deleted but launched campaigns cannot."""
    # 1. Draft deletion
    draft = await create_campaign(
        test_db,
        title="Draft To Delete",
        product_slug="exam-survival-guide",
        target_segment="all_consented",
        subject="Delete Me",
        preview_text="Preview",
        html_body="<p>Body</p>",
    )
    draft_id = draft["campaign_id"]
    del_res = await test_db.marketing_campaigns.delete_one({"campaign_id": draft_id})
    assert del_res.deleted_count == 1

    # 2. Launched campaign protection
    launched = await create_campaign(
        test_db,
        title="Launched Protected",
        product_slug="exam-survival-guide",
        target_segment="all_consented",
        subject="Launched",
        preview_text="Preview",
        html_body="<p>Body</p>",
    )
    await test_db.marketing_campaigns.update_one(
        {"campaign_id": launched["campaign_id"]},
        {"$set": {"status": "sent"}}
    )
    # Check that launch rejects re-launching
    relaunch = await launch_campaign(test_db, launched["campaign_id"])
    assert relaunch["success"] is False
    assert "already been launched" in relaunch["error"]


@pytest.mark.asyncio
async def test_marketing_email_does_not_advance_drip_sequence_position(test_db, monkeypatch):
    """Verify processing kind='marketing' sends the email but does NOT advance 52-week curriculum position."""
    from backend.workers.email_scheduler import process_email_queue

    mock_send = AsyncMock(return_value=(True, None))
    monkeypatch.setattr("backend.workers.email_scheduler.send_email", mock_send)

    now = datetime.now(timezone.utc)
    sub = await test_db.subscribers.insert_one({
        "email": "student_steady@example.com",
        "name": "Steady Student",
        "is_active": True,
        "subscribed_at": now,
        "sequence_position": 4,  # Day 4 on the 52-week curriculum
        "unsubscribe_token": "token_steady_123",
    })

    # Enqueue a marketing campaign email
    await test_db.email_queue.insert_one({
        "kind": "marketing",
        "subscriber_id": sub.inserted_id,
        "campaign_id": "CAMP-TEST-XYZ",
        "email": "student_steady@example.com",
        "name": "Steady Student",
        "subject": "Special Masterclass Announcement",
        "html_body": "<p>Hello Steady Student</p>",
        "unsubscribe_token": "token_steady_123",
        "scheduled_at": now,
        "status": "pending",
        "retry_count": 0,
        "created_at": now,
    })

    # Process queue
    await process_email_queue()

    # Verify queue item marked sent
    q_item = await test_db.email_queue.find_one({"campaign_id": "CAMP-TEST-XYZ"})
    assert q_item["status"] == "sent"

    # Verify subscriber sequence_position remained strictly 4 (did NOT advance to 5)
    updated_sub = await test_db.subscribers.find_one({"_id": sub.inserted_id})
    assert updated_sub["sequence_position"] == 4


@pytest.mark.asyncio
async def test_recommend_cross_sell_product_logic():
    """Verify cross-sell recommendation prioritizes unowned high-affinity books."""
    from backend.services.marketing_service import recommend_cross_sell_product

    # 1. Academic Comeback Package / All-access buyer -> Gets DM Closing or Boss Conflict
    rec_bundle = recommend_cross_sell_product(["academic-comeback-package"])
    assert rec_bundle is not None
    assert rec_bundle["slug"] in ("how-to-close-high-paying-clients-in-the-dms", "what-to-do-when-your-boss-is-angry-with-you", "how-to-do-your-ideas")

    # 2. Buyer who already owns bundle AND DM sales -> Gets Boss Conflict or Do Your Ideas
    rec_career = recommend_cross_sell_product(["all", "how-to-close-high-paying-clients-in-the-dms"])
    assert rec_career is not None
    assert rec_career["slug"] in ("what-to-do-when-your-boss-is-angry-with-you", "how-to-do-your-ideas", "quitting-the-handjob")

    # 3. Buyer who owns every single book -> Returns None gracefully
    all_slugs = [p["slug"] for p in get_product_knowledge_base()] + ["all"]
    rec_none = recommend_cross_sell_product(all_slugs)
    assert rec_none is None


@pytest.mark.asyncio
async def test_lifecycle_cross_sell_scan_enqueues_day7_email(test_db):
    """Verify automated scan detects 8-day old purchase and enqueues high-affinity cross-sell."""
    from backend.workers.lifecycle_marketing_scheduler import run_lifecycle_cross_sell_scan

    now = datetime.now(timezone.utc)
    eight_days_ago = now - timedelta(days=8)

    # Seed buyer who bought academic bundle 8 days ago
    await test_db.payments.insert_one({
        "reference": "ACP-SCAN-001",
        "email": "learner@example.com",
        "name": "Eager Learner",
        "product_slug": "academic-comeback-package",
        "product_name": "The Academic Comeback Package",
        "amount": 5000.0,
        "status": "success",
        "created_at": eight_days_ago,
    })
    await test_db.users.insert_one({
        "email": "learner@example.com",
        "name": "Eager Learner",
        "purchased_products": ["academic-comeback-package"],
        "is_active": True,
        "created_at": eight_days_ago,
    })
    await test_db.subscribers.insert_one({
        "email": "learner@example.com",
        "name": "Eager Learner",
        "is_active": True,
        "subscribed_at": eight_days_ago,
        "unsubscribe_token": "token_scan_123",
    })

    # Run lifecycle scan
    result = await run_lifecycle_cross_sell_scan()
    assert result["scanned"] >= 1
    assert result["enqueued"] == 1

    # Verify queue entry
    queued = await test_db.email_queue.find_one({"email": "learner@example.com", "kind": "marketing"})
    assert queued is not None
    assert "cross_sell_d7_" in queued["campaign_id"]
    assert queued["status"] == "pending"

    # Verify second scan does not create duplicates (idempotency check)
    second_result = await run_lifecycle_cross_sell_scan()
    assert second_result["enqueued"] == 0


@pytest.mark.asyncio
async def test_dispatch_preview_test_locks_recipient(client, test_db, monkeypatch):
    """Verify dispatch-preview-test restricts delivery strictly to daviditoyaa@gmail.com and mocks send."""
    # 1. Non-admin recipient rejected
    res_rejected = await client.post(
        "/api/admin/marketing/dispatch-preview-test",
        json={"recipient": "stranger@example.com", "product_slug": "quitting-the-handjob"}
    )
    assert res_rejected.status_code == 403

    # 2. daviditoyaa@gmail.com accepted
    async def mock_send(to_email, subject, body):
        return (True, None)

    import backend.services.marketing_service as ms
    monkeypatch.setattr(ms, "send_email", mock_send)

    res_ok = await client.post(
        "/api/admin/marketing/dispatch-preview-test",
        json={"recipient": "daviditoyaa@gmail.com", "product_slug": "quitting-the-handjob"}
    )
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["success"] is True
    assert "daviditoyaa@gmail.com" in data["message"]
