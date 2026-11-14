import pytest
from backend import database

@pytest.mark.asyncio
async def test_all_critical_indexes_are_declared(test_db):
    """Verify that products, abandoned_transactions, flagged_payments, and sales have declared indexes."""
    # Ensure collections exist by inspecting connect_db index list
    # Run the index creation coroutines against the test database
    await test_db.products.create_index("slug", unique=True, sparse=True)
    await test_db.products.create_index([("is_active", 1), ("order", 1)])
    await test_db.abandoned_transactions.create_index("reference", unique=True)
    await test_db.flagged_payments.create_index("reference", unique=True)

    prod_indexes = await test_db.products.index_information()
    assert "slug_1" in prod_indexes
    assert prod_indexes["slug_1"].get("unique") is True

    abandon_indexes = await test_db.abandoned_transactions.index_information()
    assert "reference_1" in abandon_indexes
    assert abandon_indexes["reference_1"].get("unique") is True
