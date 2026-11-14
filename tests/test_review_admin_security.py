import pytest
from bson import ObjectId
from backend.utils.security import create_access_token

@pytest.mark.asyncio
async def test_review_moderation_unauthenticated_blocked(client, test_db):
    """Unauthenticated requests to approve/reject reviews must be blocked with 401."""
    fake_id = str(ObjectId())
    
    # Attempt approve
    res_approve = await client.post(f"/api/admin/reviews/{fake_id}/approve")
    assert res_approve.status_code == 401
    
    # Attempt reject
    res_reject = await client.post(f"/api/admin/reviews/{fake_id}/reject")
    assert res_reject.status_code == 401

@pytest.mark.asyncio
async def test_review_moderation_non_admin_blocked(client, test_db):
    """Customer or sales_rep role requests to approve/reject must be blocked with 403."""
    user_res = await test_db.users.insert_one({
        "email": "customer@example.com",
        "name": "Normal Customer",
        "is_active": True,
    })
    token = create_access_token({"sub": str(user_res.inserted_id), "email": "customer@example.com", "role": "customer"})
    headers = {"Authorization": f"Bearer {token}"}
    fake_id = str(ObjectId())

    res_approve = await client.post(f"/api/admin/reviews/{fake_id}/approve", headers=headers)
    assert res_approve.status_code == 403

    res_reject = await client.post(f"/api/admin/reviews/{fake_id}/reject", headers=headers)
    assert res_reject.status_code == 403

@pytest.mark.asyncio
async def test_review_moderation_admin_allowed(client, test_db):
    """Admin credentials can approve and reject reviews."""
    admin_token = create_access_token({"sub": "admin", "email": "admin@academic-pack.com", "role": "admin"})
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Seed a review
    review_res = await test_db.reviews.insert_one({
        "name": "Jane Doe",
        "rating": 5,
        "text": "Great book, transformed my habits!",
        "approved": False,
    })
    review_id = str(review_res.inserted_id)

    # Approve
    res_approve = await client.post(f"/api/admin/reviews/{review_id}/approve", headers=headers)
    assert res_approve.status_code == 200
    updated = await test_db.reviews.find_one({"_id": review_res.inserted_id})
    assert updated["approved"] is True

    # Reject
    res_reject = await client.post(f"/api/admin/reviews/{review_id}/reject", headers=headers)
    assert res_reject.status_code == 200
    updated2 = await test_db.reviews.find_one({"_id": review_res.inserted_id})
    assert updated2["approved"] is False
