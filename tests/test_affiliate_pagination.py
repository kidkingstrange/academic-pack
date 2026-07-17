"""
Regression coverage for audit Medium #22: affiliate lists were hard-capped
at to_list(500), silently dropping anything beyond it, with no way to see
the rest. Both the admin-only GET /api/admin/affiliates and the
Affiliates Engine tab's GET /api/admin/analytics/affiliates now paginate
properly and report total/page/pages instead of silently truncating.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from backend.utils.security import create_access_token


async def _admin_headers(test_db):
    admin_id = (await test_db.admin_accounts.insert_one({
        "email": "paginationadmin@example.com", "password_hash": "x",
    })).inserted_id
    token = create_access_token({"sub": str(admin_id), "email": "paginationadmin@example.com", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


async def _seed_affiliates(test_db, count):
    now = datetime.now(timezone.utc)
    docs = [
        {"code": f"AFF{i:04d}", "name": f"Affiliate {i}", "email": f"aff{i}@example.com",
         "active": True, "commission_percent": 50, "created_at": now}
        for i in range(count)
    ]
    await test_db.affiliates.insert_many(docs)


@pytest.mark.asyncio
async def test_affiliates_list_not_silently_capped_beyond_default_page(client, test_db):
    await _seed_affiliates(test_db, 120)
    headers = await _admin_headers(test_db)

    res = await client.get("/api/admin/affiliates?limit=200", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 120
    assert len(data["affiliates"]) == 120


@pytest.mark.asyncio
async def test_affiliates_list_pagination_metadata_correct(client, test_db):
    await _seed_affiliates(test_db, 45)
    headers = await _admin_headers(test_db)

    res = await client.get("/api/admin/affiliates?page=1&limit=20", headers=headers)
    data = res.json()
    assert data["total"] == 45
    assert data["page"] == 1
    assert data["pages"] == 3
    assert len(data["affiliates"]) == 20

    res2 = await client.get("/api/admin/affiliates?page=3&limit=20", headers=headers)
    assert len(res2.json()["affiliates"]) == 5


@pytest.mark.asyncio
async def test_analytics_affiliates_endpoint_no_longer_silently_drops_past_500(client, test_db):
    await _seed_affiliates(test_db, 600)
    headers = await _admin_headers(test_db)

    res = await client.get("/api/admin/analytics/affiliates?limit=1000", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 600
    assert len(data["affiliates"]) == 600
