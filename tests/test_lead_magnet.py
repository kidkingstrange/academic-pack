"""
Unit and integration tests for Lead Magnet Opt-In and Viral Referral Engine.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_lead_magnet_opt_in_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/lead-magnet/opt-in",
            json={
                "name": "Test Growth Lead",
                "email": "testgrowthlead@example.com",
                "category": "Sales & DM Closing"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "ref_code" in data
        assert "referral_link" in data
        assert data["ref_code"].startswith("SCALE-")

@pytest.mark.asyncio
async def test_lead_magnet_referral_tracking():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create referrer
        ref_res = await client.post(
            "/api/lead-magnet/opt-in",
            json={
                "name": "Referrer User",
                "email": "referrer@example.com",
                "category": "Sales & DM Closing"
            }
        )
        assert ref_res.status_code == 200
        ref_code = ref_res.json()["ref_code"]

        # 2. Referred user signs up using referral_code
        refed_res = await client.post(
            "/api/lead-magnet/opt-in",
            json={
                "name": "Referred Friend",
                "email": "friend@example.com",
                "category": "Business & Scale",
                "referral_code": ref_code
            }
        )
        assert refed_res.status_code == 200

        # 3. Check referrer's updated stats
        stats_res = await client.get(f"/api/lead-magnet/referral-stats/{ref_code}")
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["ref_code"] == ref_code
        assert stats["referrals_count"] >= 1
