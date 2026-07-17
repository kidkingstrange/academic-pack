"""
Regression coverage for audit Medium #20: the nudge scheduler used to run
a separate count_documents + find_one per candidate affiliate code inside a
loop. Batched into two upfront queries — this test checks the *outcome* is
unchanged (an affiliate who already clicked their own link is skipped and
marked nudge_sent; one who hasn't gets a nudge email queued).
"""
import pytest
from datetime import datetime, timezone, timedelta

from backend.workers.affiliate_nudge_scheduler import run_nudge_check


@pytest.mark.asyncio
async def test_affiliate_with_existing_click_is_skipped_not_nudged(test_db):
    old = datetime.now(timezone.utc) - timedelta(days=5)
    await test_db.affiliates.insert_one({"code": "CLICKER", "email": "clicker@example.com", "name": "Clicker"})
    await test_db.marketing_asset_downloads.insert_one({
        "affiliate_code": "CLICKER", "downloaded_at": old, "nudge_sent": False,
    })
    await test_db.referral_clicks.insert_one({"affiliate_code": "CLICKER", "clicked_at": old})

    await run_nudge_check()

    queued = await test_db.email_queue.count_documents({"kind": "affiliate_nudge", "email": "clicker@example.com"})
    assert queued == 0
    download = await test_db.marketing_asset_downloads.find_one({"affiliate_code": "CLICKER"})
    assert download["nudge_sent"] is True


@pytest.mark.asyncio
async def test_affiliate_without_click_gets_nudged(test_db):
    old = datetime.now(timezone.utc) - timedelta(days=5)
    await test_db.affiliates.insert_one({"code": "NOCLICK", "email": "noclick@example.com", "name": "No Click"})
    await test_db.marketing_asset_downloads.insert_one({
        "affiliate_code": "NOCLICK", "downloaded_at": old, "nudge_sent": False,
    })

    await run_nudge_check()

    queued = await test_db.email_queue.find_one({"kind": "affiliate_nudge", "email": "noclick@example.com"})
    assert queued is not None
    download = await test_db.marketing_asset_downloads.find_one({"affiliate_code": "NOCLICK"})
    assert download["nudge_sent"] is True


@pytest.mark.asyncio
async def test_duplicate_candidate_across_download_and_video_click_nudged_once(test_db):
    old = datetime.now(timezone.utc) - timedelta(days=5)
    await test_db.affiliates.insert_one({"code": "DUPCODE", "email": "dup@example.com", "name": "Dup"})
    await test_db.marketing_asset_downloads.insert_one({
        "affiliate_code": "DUPCODE", "downloaded_at": old, "nudge_sent": False,
    })
    await test_db.marketing_video_clicks.insert_one({
        "affiliate_code": "DUPCODE", "clicked_at": old, "nudge_sent": False,
    })

    await run_nudge_check()

    count = await test_db.email_queue.count_documents({"kind": "affiliate_nudge", "email": "dup@example.com"})
    assert count == 1
