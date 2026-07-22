"""
Unit & Integration Tests for Abandoned Transaction Recovery System.
"""
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from backend.services.abandoned_recovery_service import (
    record_checkout_initialization,
    mark_transaction_recovered,
    is_buyer,
    is_unsubscribed,
    unsubscribe_email,
)
from backend.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_record_checkout_initialization(test_db):
    email = "test_abandoned_user@example.com"
    ref = "ACP-TEST-ABANDON-001"

    # Record checkout init
    tx = await record_checkout_initialization(
        test_db,
        email=email,
        name="Test Abandoned Student",
        amount=2000.0,
        currency="NGN",
        reference=ref,
    )

    assert tx["reference"] == ref
    assert tx["email"] == email.lower()
    assert tx["status"] == "pending"

    # Verify saved in db
    saved = await test_db.abandoned_transactions.find_one({"reference": ref})
    assert saved is not None
    assert saved["email"] == email.lower()


@pytest.mark.asyncio
async def test_mark_transaction_recovered(test_db):
    email = "test_recovery_buyer@example.com"
    ref = "ACP-TEST-RECOVER-002"

    await record_checkout_initialization(
        test_db,
        email=email,
        name="Recovery Student",
        amount=2000.0,
        currency="NGN",
        reference=ref,
    )

    # Mark as recovered
    count = await mark_transaction_recovered(test_db, reference=ref)
    assert count >= 1

    saved = await test_db.abandoned_transactions.find_one({"reference": ref})
    assert saved["status"] == "recovered"
    assert saved["recovered_at"] is not None


@pytest.mark.asyncio
async def test_unsubscribe_handling(test_db):
    email = "test_unsub_student@example.com"
    ref = "ACP-TEST-UNSUB-003"

    await record_checkout_initialization(
        test_db,
        email=email,
        name="Unsub Student",
        amount=2000.0,
        currency="NGN",
        reference=ref,
    )

    assert not (await is_unsubscribed(test_db, email))

    # Perform unsubscribe
    await unsubscribe_email(test_db, email)

    assert await is_unsubscribed(test_db, email)

    saved = await test_db.abandoned_transactions.find_one({"reference": ref})
    assert saved["status"] == "unsubscribed"


@pytest.mark.asyncio
async def test_buyer_guard(test_db):
    email = "test_existing_buyer@example.com"
    now = datetime.now(timezone.utc)

    # Insert a successful payment
    await test_db.payments.insert_one({
        "reference": "ACP-SUCCESS-PAID",
        "email": email,
        "amount": 2000.0,
        "status": "success",
        "verified_at": now,
    })

    assert await is_buyer(test_db, email)


@pytest.mark.asyncio
async def test_step4_email_and_price(test_db, monkeypatch):
    from backend.services import abandoned_recovery_service as recovery_module
    from unittest.mock import AsyncMock

    # send_email would otherwise open a real SMTP connection — same
    # mocking pattern every other test in this suite already uses.
    # Patched on the module it was imported into (recovery_module),
    # not email_service itself, since `from ..services.email_service
    # import send_email` already bound its own local reference there.
    monkeypatch.setattr(recovery_module, "send_email", AsyncMock(return_value=(True, None)))

    email = "test_step4_student@example.com"
    ref = "ACP-TEST-STEP4-004"

    tx = await record_checkout_initialization(
        test_db,
        email=email,
        name="Step4 Student",
        amount=5000.0,  # Originally initialized at late price ₦5,000
        currency="NGN",
        reference=ref,
    )

    # Sending step 4 email should succeed and offer ₦2,000 price
    sent = await recovery_module.send_recovery_email_step(test_db, tx, step=4)
    assert sent is True

    saved = await test_db.abandoned_transactions.find_one({"reference": ref})
    assert saved["sequence_step"] == 4
    assert len(saved["emails_sent"]) == 1
    assert "2,000" in saved["emails_sent"][0]["subject"]


