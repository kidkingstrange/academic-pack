"""
Comprehensive test suite for the Automated Customer Review & Social Proof System.
"""
import io
import pytest
from datetime import datetime, timedelta, timezone
from PIL import Image

from backend.utils.review_token import generate_review_token, verify_review_token, hash_review_token
from backend.services.image_service import process_and_save_webp, validate_image_bytes
from backend.services.review_moderation import evaluate_review_moderation
from backend.services.coupon_service import issue_review_coupon
from backend.workers.review_scheduler import process_review_requests


@pytest.fixture
def sample_jpeg_bytes():
    """Generates a small valid test JPEG in memory."""
    buf = io.BytesIO()
    img = Image.new("RGB", (200, 200), color=(212, 166, 58))
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_token_generation_and_tamper_rejection():
    # 1. Generate valid token
    ref = "ACP-TEST-12345"
    email = "student@example.com"
    name = "Chidi Okafor"
    token = generate_review_token(ref, email, name)

    assert token is not None
    assert "." in token

    # 2. Verify valid token
    payload = verify_review_token(token)
    assert payload is not None
    assert payload["ref"] == ref
    assert payload["email"] == email
    assert payload["name"] == name

    # 3. Tampered payload or signature
    tampered = token[:-4] + "abcd"
    assert verify_review_token(tampered) is None

    # 4. Completely invalid string
    assert verify_review_token("not-a-token") is None
    assert verify_review_token("") is None


@pytest.mark.asyncio
async def test_image_validation_exif_strip_and_webp_conversion(sample_jpeg_bytes):
    # 1. Test validation on valid bytes
    is_valid, msg = validate_image_bytes(sample_jpeg_bytes)
    assert is_valid is True

    # 2. Test rejection on garbage data
    is_valid, msg = validate_image_bytes(b"not-an-image-data")
    assert is_valid is False

    # 3. Test WebP conversion
    success, url, err = process_and_save_webp(sample_jpeg_bytes)
    assert success is True
    assert url is not None
    assert url.startswith("/uploads/reviews/rev_")
    assert url.endswith(".webp")
    assert err is None


@pytest.mark.asyncio
async def test_review_moderation_rules():
    # 5 stars clean text -> auto approved
    appr, reason = evaluate_review_moderation(5, "This package completely changed my reading habits!")
    assert appr is True
    assert reason == "auto_approved_high_rating"

    # 4 stars clean text -> auto approved
    appr, reason = evaluate_review_moderation(4, "Very solid exam preparation techniques and templates.")
    assert appr is True
    assert reason == "auto_approved_high_rating"

    # 3 stars -> requires manual approval
    appr, reason = evaluate_review_moderation(3, "Decent material, but took some time to finish.")
    assert appr is False
    assert reason == "pending_manual_review_low_rating"

    # Flagged spam keywords -> rejected / manual review even with 5 stars
    appr, reason = evaluate_review_moderation(5, "Great book! Check out my crypto bitcoin casino at http://spam.com")
    assert appr is False
    assert reason == "flagged_keyword_or_link"


@pytest.mark.asyncio
async def test_coupon_issuance(test_db):
    email = "reviewer_test@example.com"
    name = "Tunde"

    code = await issue_review_coupon(test_db, email, name)
    assert code is not None
    assert code.startswith("REV20-")

    coupon = await test_db.coupons.find_one({"code": code})
    assert coupon is not None
    assert coupon["issued_to"] == email
    assert coupon["discount_percent"] == 20
    assert coupon["used"] is False


@pytest.mark.asyncio
async def test_review_submission_api_and_single_use_guard(client, test_db, sample_jpeg_bytes):
    ref = "ACP-REV-PAYMENT-1"
    email = "jane.review@example.com"
    name = "Jane Doe"
    token = generate_review_token(ref, email, name)

    # 1. Submit review with photo
    response = await client.post(
        "/api/reviews",
        data={
            "token": token,
            "rating": "5",
            "text": "The 20-minute protocol cut my reading time down drastically! 100% recommended.",
            "display_name": "Jane D.",
        },
        files={
            "photo": ("test.jpg", sample_jpeg_bytes, "image/jpeg"),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["approved"] is True
    assert data["coupon_code"].startswith("REV20-")

    # Verify review in MongoDB
    saved = await test_db.reviews.find_one({"email": email})
    assert saved is not None
    assert saved["rating"] == 5
    assert saved["name"] == "Jane D."
    assert saved["photo_url"] is not None
    assert saved["approved"] is True

    # 2. Attempt duplicate submission on same token (Single-use guard)
    dup_response = await client.post(
        "/api/reviews",
        data={
            "token": token,
            "rating": "5",
            "text": "Trying to submit again for extra coupons.",
        },
    )
    assert dup_response.status_code == 400
    assert "already been submitted" in dup_response.json()["detail"]


@pytest.mark.asyncio
async def test_reviews_listing_and_summary_endpoints(client, test_db):
    # Seed test approved reviews
    await test_db.reviews.delete_many({})
    await test_db.reviews.insert_many([
        {"email": "u1@test.com", "name": "User 1", "rating": 5, "text": "Superb 5-star review", "approved": True, "date": datetime.now(timezone.utc)},
        {"email": "u2@test.com", "name": "User 2", "rating": 5, "text": "Another great review", "approved": True, "date": datetime.now(timezone.utc)},
        {"email": "u3@test.com", "name": "User 3", "rating": 4, "text": "Solid 4-star material", "approved": True, "date": datetime.now(timezone.utc)},
        {"email": "u4@test.com", "name": "User 4", "rating": 2, "text": "Unapproved 2-star", "approved": False, "date": datetime.now(timezone.utc)},
    ])

    from backend.routes.reviews import invalidate_reviews_cache
    invalidate_reviews_cache()

    # 1. Test Summary
    sum_res = await client.get("/api/reviews/summary")
    assert sum_res.status_code == 200
    sum_data = sum_res.json()
    assert sum_data["total_reviews"] == 3  # only approved
    # (5 + 5 + 4) / 3 = 14 / 3 = 4.7
    assert sum_data["average_rating"] == 4.7
    assert sum_data["breakdown"]["5"] == 2
    assert sum_data["breakdown"]["4"] == 1

    # 2. Test List
    list_res = await client.get("/api/reviews?approved=true&limit=10&offset=0")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert len(list_data["reviews"]) == 3
    assert list_data["total"] == 3


@pytest.mark.asyncio
async def test_scheduled_review_request_trigger(test_db, monkeypatch):
    # Clear payments
    await test_db.payments.delete_many({"reference": "ACP-SCHED-TEST"})

    # Insert a purchase made 6 days ago
    six_days_ago = datetime.now(timezone.utc) - timedelta(days=6)
    await test_db.payments.insert_one({
        "reference": "ACP-SCHED-TEST",
        "email": "eligible.customer@example.com",
        "name": "Segun",
        "status": "success",
        "created_at": six_days_ago,
        "verified_at": six_days_ago,
        "review_request_sent": False,
    })

    # Track sent emails
    sent_emails = []
    async def mock_send_email(to, sub, html):
        sent_emails.append({"to": to, "sub": sub, "html": html})
        return True, None

    monkeypatch.setattr("backend.workers.review_scheduler.send_email", mock_send_email)

    count = await process_review_requests(test_db)
    assert count == 1
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "eligible.customer@example.com"
    assert "Quick 60-second check-in" in sent_emails[0]["html"] or "review" in sent_emails[0]["html"].lower()

    # Verify payment marked as sent
    p = await test_db.payments.find_one({"reference": "ACP-SCHED-TEST"})
    assert p["review_request_sent"] is True
    assert p.get("review_token") is not None
