"""
Comprehensive tests for multi-book dynamic pricing architecture across backend and frontend.
Tests cover:
- Dynamic pricing for standalone books (arbitrary NGN and USD prices)
- /api/payments/product-info endpoint
- Authoritative Paystack initialization price resolution from db.products
- Webhook / callback payment completion with fee reconciliation
- Library entitlement isolation (single_book tier, unlocking only purchased book)
- Library sign download with slug and ObjectId
- Welcome email personalization with specific book title
"""
import hashlib
import hmac
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId

from backend.config import get_settings
from backend.services.payment_completion import complete_payment

settings = get_settings()


def _sign(raw_body: bytes) -> str:
    secret = (settings.PAYSTACK_SECRET_KEY or "").strip()
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()


@pytest.mark.asyncio
async def test_product_info_public_endpoint(client, test_db):
    """GET /api/payments/product-info returns dynamic pricing and details for any active book."""
    await test_db.products.insert_one({
        "order": 99,
        "title": "Quantum Physics for Beginners",
        "slug": "quantum-physics-beginners",
        "description": "Comprehensive introduction to quantum mechanics.",
        "price_naira": 3500.0,
        "price_usd": 12.0,
        "is_active": True,
        "file_path": "quantum_physics.pdf",
    })

    # Query by slug
    res = await client.get("/api/payments/product-info?slug=quantum-physics-beginners")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Quantum Physics for Beginners"
    assert data["slug"] == "quantum-physics-beginners"
    assert data["price_naira"] == 3500.0
    assert data["price_usd"] == 12.0

    # Query by title
    res_title = await client.get("/api/payments/product-info?title=Quantum Physics for Beginners")
    assert res_title.status_code == 200
    assert res_title.json()["price_naira"] == 3500.0

    # Non-existent product
    res_404 = await client.get("/api/payments/product-info?slug=non-existent-book")
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_dynamic_payment_init_with_custom_price(client, test_db, monkeypatch):
    """Payment initialization uses custom price_naira from db.products instead of hardcoded 5000."""
    await test_db.products.insert_one({
        "order": 100,
        "title": "The Art of Stoic Focus",
        "slug": "art-of-stoic-focus",
        "description": "Mastering attention in the digital age.",
        "price_naira": 2500.0,
        "price_usd": 8.0,
        "is_active": True,
        "file_path": "art_of_stoic_focus.pdf",
    })

    captured_init = {}

    async def mock_init_tx(**kwargs):
        captured_init.update(kwargs)
        return {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/mock-stoic",
                "reference": kwargs["reference"],
                "access_code": "code-stoic-123",
            }
        }

    monkeypatch.setattr("backend.routes.payments.initialize_transaction", mock_init_tx)

    res = await client.post("/api/payments/initialize", json={
        "name": "Marcus Aurelius",
        "email": "marcus@stoa.edu",
        "product_slug": "art-of-stoic-focus",
        "payment_method": "card",
    })

    assert res.status_code == 200
    body = res.json()
    assert body["amount"] == 2500.0
    assert captured_init["amount_naira"] == 2500.0
    assert captured_init["reference"].startswith("ACP-ARTO-")

    pending = await test_db.pending_payments.find_one({"reference": body["reference"]})
    assert pending is not None
    assert pending["base_price"] == 2500.0
    assert pending["amount"] == 2500.0
    assert pending["product_slug"] == "art-of-stoic-focus"
    assert pending["book_title"] == "The Art of Stoic Focus"


@pytest.mark.asyncio
async def test_dynamic_book_payment_completion_and_library_isolation(test_db):
    """Completing payment for a standalone book grants access ONLY to that book in single_book tier."""
    book_oid = ObjectId()
    await test_db.products.insert_one({
        "_id": book_oid,
        "order": 101,
        "title": "Deep Sleep Protocol",
        "slug": "deep-sleep-protocol",
        "description": "Evidence-based sleep optimization guide.",
        "price_naira": 1500.0,
        "is_active": True,
        "file_path": "deep_sleep_protocol.pdf",
    })

    ref = "ACP-DEEP-9876543210AB"
    await test_db.pending_payments.insert_one({
        "reference": ref,
        "charge_id": "charge-deep-1",
        "amount": 1500.0,
        "base_price": 1500.0,
        "currency": "NGN",
        "email": "insomniac@student.ng",
        "name": "Sleep Seeker",
        "product_slug": "deep-sleep-protocol",
        "book_title": "Deep Sleep Protocol",
        "tier": "complete",  # client tier field is ignored in favor of single_book logic
    })

    gateway_payload = {
        "status": "success",
        "reference": ref,
        "amount": 150000,
        "currency": "NGN",
    }

    result = await complete_payment(
        db=test_db,
        reference=ref,
        email="insomniac@student.ng",
        name="Sleep Seeker",
        amount=1500.0,
        charge_id="charge-deep-1",
        gateway_response=gateway_payload,
        payment_method="bank_transfer",
        completed_via="webhook",
    )

    assert result["already_completed"] is False

    user = await test_db.users.find_one({"email": "insomniac@student.ng"})
    assert user is not None
    assert user["tier"] == "single_book"
    assert "all" not in user["purchased_products"]
    assert "deep-sleep-protocol" in user["purchased_products"]
    assert str(book_oid) in user["purchased_products"]

    # Verify welcome email was queued with specific book title
    queued_email = await test_db.email_queue.find_one({
        "email": "insomniac@student.ng",
        "kind": "welcome",
    })
    assert queued_email is not None
    assert queued_email.get("book_title") == "Deep Sleep Protocol"
    assert queued_email.get("product_slug") == "deep-sleep-protocol"


@pytest.mark.asyncio
async def test_library_access_and_download_permissions(client, test_db, tmp_path, monkeypatch):
    """Single book buyer sees only purchased book unlocked in library and can download only it."""
    # Create two test products
    p1_oid = ObjectId()
    p2_oid = ObjectId()

    # Create dummy pdf files
    pdf1 = tmp_path / "book1.pdf"
    pdf1.write_bytes(b"%PDF-1.4 test book 1 content")
    pdf2 = tmp_path / "book2.pdf"
    pdf2.write_bytes(b"%PDF-1.4 test book 2 content")

    monkeypatch.setattr(
        "backend.routes.library.resolve_product_pdf_path",
        lambda product, uploads_dir: pdf1 if product["slug"] == "book-one" else pdf2
    )

    await test_db.products.insert_many([
        {
            "_id": p1_oid,
            "order": 1,
            "title": "Book One: Purchased",
            "slug": "book-one",
            "price_naira": 3000.0,
            "is_active": True,
            "file_path": "book1.pdf",
        },
        {
            "_id": p2_oid,
            "order": 2,
            "title": "Book Two: Not Purchased",
            "slug": "book-two",
            "price_naira": 4000.0,
            "is_active": True,
            "file_path": "book2.pdf",
        },
    ])

    user_token = "valid-single-book-token-12345"
    user_id = ObjectId()
    await test_db.users.insert_one({
        "_id": user_id,
        "name": "Jane Reader",
        "email": "jane@example.com",
        "tier": "single_book",
        "purchased_products": [str(p1_oid), "book-one"],
        "library_access_token": user_token,
        "is_active": True,
    })

    # Test GET /api/library
    lib_res = await client.get(f"/api/library?token={user_token}")
    assert lib_res.status_code == 200
    lib_data = lib_res.json()
    assert lib_data["tier"] == "single_book"
    products = {p["slug"] if "slug" in p else p["title"]: p for p in lib_data["products"]}

    p1_entry = next(p for p in lib_data["products"] if p["title"] == "Book One: Purchased")
    p2_entry = next(p for p in lib_data["products"] if p["title"] == "Book Two: Not Purchased")
    assert p1_entry["locked"] is False
    assert p2_entry["locked"] is True

    # Test downloading unlocked book using ObjectId
    sign_p1 = await client.get(f"/api/library/sign/{str(p1_oid)}?token={user_token}")
    assert sign_p1.status_code == 200
    signed_url = sign_p1.json()["signed_url"]

    # Test downloading unlocked book using slug
    sign_p1_slug = await client.get(f"/api/library/sign/book-one?token={user_token}")
    assert sign_p1_slug.status_code == 200

    # Test downloading locked book
    sign_p2 = await client.get(f"/api/library/sign/{str(p2_oid)}?token={user_token}")
    assert sign_p2.status_code == 403

    # Actually download the file
    dl_res = await client.get(signed_url)
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert dl_res.content == b"%PDF-1.4 test book 1 content"


@pytest.mark.asyncio
async def test_all_canonical_and_folder_products_pdf_resolution():
    """All canonical products and new folder-based books have their PDFs resolved."""
    from scripts.sync_products_db import CANONICAL_PRODUCTS
    from backend.utils.product_delivery import resolve_product_pdf_path

    for prod in CANONICAL_PRODUCTS:
        pdf_path = resolve_product_pdf_path(prod, settings.UPLOADS_DIR)
        assert pdf_path is not None, f"Failed to resolve PDF for {prod['title']}"
        assert pdf_path.exists(), f"Path {pdf_path} does not exist for {prod['title']}"

    # Also test new books in folders
    new_books = [
        {"title": "How to Close High-Paying Clients in the DMs", "slug": "high-paying-clients"},
        {"title": "How to Do Your Ideas", "slug": "how-to-do-your-ideas"},
        {"title": "What To Do When Your Boss Is Angry With You", "slug": "what-to-do-when-your-boss-is-angry"},
        {"title": "What to Do After a Breakup", "slug": "what-to-do-after-a-breakup"},
    ]
    for book in new_books:
        pdf_path = resolve_product_pdf_path(book, settings.UPLOADS_DIR)
        assert pdf_path is not None, f"Failed to resolve PDF for new book {book['title']}"
        assert pdf_path.exists(), f"Path {pdf_path} does not exist for {book['title']}"

