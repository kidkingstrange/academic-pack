"""
Shared pytest fixtures.

Tests never touch the real Atlas cluster's app data — each test run gets its
own throwaway database (same MongoDB Atlas connection, unique DB name),
dropped at teardown. The FastAPI app's own lifespan (schedulers, etc.) is
never started; routes only need `backend.database.db` pointed at the scratch
database via `Depends(get_db)`.
"""
import os
import re
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

os.environ.setdefault("APP_ENV", "development")


def _load_dotenv_into_environ():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line.rstrip("\n"))
            if m and m.group(1) not in os.environ:
                os.environ[m.group(1)] = m.group(2)


import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend import database  # noqa: E402
from backend.main import app  # noqa: E402


@pytest_asyncio.fixture
async def test_db():
    mongo_url = os.environ.get("MONGODB_URL") or os.environ.get("MONGO_URI", "mongodb://127.0.0.1:27017")
    # Short prefix + a slice of uuid4 hex, not a millisecond timestamp —
    # tests in the same file can start within the same millisecond and
    # would otherwise collide onto the same scratch database name, leaking
    # data between supposedly-isolated tests. Atlas caps DB names at 38
    # bytes, so this can't just be the full 32-char hex on a longer prefix.
    db_name = f"acp_test_{uuid.uuid4().hex[:16]}"
    conn = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
    scratch = conn[db_name]

    prev_client, prev_db = database.client, database.db
    database.client, database.db = conn, scratch
    try:
        yield scratch
    finally:
        await conn.drop_database(db_name)
        conn.close()
        database.client, database.db = prev_client, prev_db


@pytest_asyncio.fixture
async def client(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
