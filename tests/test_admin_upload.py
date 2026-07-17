"""
Regression coverage for audit Medium #26: the admin product-upload path
wrote the uploaded file synchronously on the event loop, freezing request
handling for every other concurrent user for the duration of the write.
Moved to a worker thread via run_in_threadpool — this test just confirms
the upload still actually writes the correct bytes to disk and the
product record is created, since that's what the threadpool move could
plausibly break if done wrong (e.g. capturing the wrong closure variable).
"""
import os
import shutil
import pytest

from backend.config import get_settings
from backend.utils.security import create_access_token

settings = get_settings()


@pytest.mark.asyncio
async def test_uploaded_pdf_is_written_correctly_to_disk(client, test_db):
    admin_id = (await test_db.admin_accounts.insert_one({
        "email": "uploadadmin@example.com", "password_hash": "x",
    })).inserted_id
    token = create_access_token({"sub": str(admin_id), "email": "uploadadmin@example.com", "role": "admin"})

    file_content = b"%PDF-1.4 fake pdf content for test\n" * 100
    expected_path = os.path.join(settings.UPLOADS_DIR, "test_upload_regression.pdf")
    if os.path.exists(expected_path):
        os.remove(expected_path)

    try:
        res = await client.post(
            "/api/admin/products",
            headers={"Authorization": f"Bearer {token}"},
            data={"title": "Test Book", "description": "A test", "order": "1"},
            files={"file": ("test_upload_regression.pdf", file_content, "application/pdf")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Test Book"

        assert os.path.exists(expected_path)
        with open(expected_path, "rb") as f:
            assert f.read() == file_content

        product = await test_db.products.find_one({"_id": __import__("bson").ObjectId(data["id"])})
        assert product is not None
        assert product["file_path"] == "test_upload_regression.pdf"
    finally:
        if os.path.exists(expected_path):
            os.remove(expected_path)
