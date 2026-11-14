import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app

@pytest.mark.asyncio
async def test_direct_pdf_access_is_blocked(client):
    """Direct unauthenticated access to /pdfs/... must return 403 Forbidden with library guidance."""
    resp = await client.get("/pdfs/Quitting_The_Handjob_David_Itoya.pdf")
    assert resp.status_code == 403
    assert "Protected Digital Asset" in resp.text
    assert "Go to My Library" in resp.text

@pytest.mark.asyncio
async def test_direct_upload_product_pdf_access_is_blocked(client):
    """Direct unauthenticated access to /uploads/products/... must return 403 Forbidden with library guidance."""
    resp = await client.get("/uploads/products/30-Day_Study_Tracker.pdf")
    assert resp.status_code == 403
    assert "Protected Digital Asset" in resp.text
    assert "Go to My Library" in resp.text
