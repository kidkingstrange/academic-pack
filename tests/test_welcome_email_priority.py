import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from backend.config import Settings
from backend.main import check_app_url_configured_for_production
from backend.workers.email_scheduler import process_email_queue


def test_startup_guard_fails_production_with_localhost():
    s = Settings(APP_ENV="production", APP_URL="http://localhost:8000")
    with pytest.raises(RuntimeError, match="CRITICAL CONFIGURATION ERROR"):
        check_app_url_configured_for_production(s)

    s2 = Settings(APP_ENV="production", APP_URL="http://127.0.0.1:8000")
    with pytest.raises(RuntimeError, match="CRITICAL CONFIGURATION ERROR"):
        check_app_url_configured_for_production(s2)

    s_ok = Settings(APP_ENV="production", APP_URL="https://thescaleconference.com")
    # Should not raise exception
    check_app_url_configured_for_production(s_ok)


@pytest.mark.asyncio
async def test_process_email_queue_prioritizes_welcome_over_sequence():
    now = datetime.now(timezone.utc)
    welcome_item = {
        "_id": "item1",
        "kind": "welcome",
        "email": "customer@example.com",
        "name": "Jane Customer",
        "access_token": "token123",
        "status": "sending"
    }

    mock_db = AsyncMock()

    # Return welcome_item on first find_one_and_update call, then None
    call_count = 0
    async def fake_find_one_and_update(filter_query, update_query, **kwargs):
        nonlocal call_count
        call_count += 1
        kind_filter = filter_query.get("kind", {})
        if isinstance(kind_filter, dict) and "$in" in kind_filter:
            if call_count == 1:
                return welcome_item
        return None

    mock_db.email_queue.find_one_and_update = fake_find_one_and_update
    mock_db.email_queue.update_one = AsyncMock()

    with patch("backend.workers.email_scheduler.database.get_db", return_value=mock_db), \
         patch("backend.workers.email_scheduler.send_welcome_email", AsyncMock(return_value=(True, None))) as mock_send:

        await process_email_queue()
        mock_send.assert_called_once()
        assert mock_send.call_args[1]["email"] == "customer@example.com"
