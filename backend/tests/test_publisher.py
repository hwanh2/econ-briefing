import pytest
from unittest.mock import patch, MagicMock
from app.pipeline.publisher import Publisher


@pytest.fixture
def subscribers():
    return [
        {"id": 1, "email": "alice@test.com", "name": "Alice"},
        {"id": 2, "email": "bob@test.com", "name": "Bob"},
    ]


@pytest.mark.asyncio
async def test_send_no_api_key_skips(subscribers):
    with patch("app.pipeline.publisher.settings") as mock_settings:
        mock_settings.resend_api_key = ""
        result = await Publisher().send("<h1>Test</h1>", subscribers=subscribers)
    assert result["skipped"] == 2
    assert result["sent"] == 0
    assert result["reason"] == "no_api_key"


@pytest.mark.asyncio
async def test_send_with_api_key(subscribers):
    with (
        patch("app.pipeline.publisher.settings") as mock_settings,
        patch("app.pipeline.publisher.resend") as mock_resend,
    ):
        mock_settings.resend_api_key = "re_test_key"
        mock_resend.Emails.send.return_value = {"id": "msg_123"}
        result = await Publisher().send("<h1>Test</h1>", subscribers=subscribers)
    assert result["sent"] == 2
    assert result["failed"] == 0
    assert mock_resend.Emails.send.call_count == 2


@pytest.mark.asyncio
async def test_send_partial_failure(subscribers):
    with (
        patch("app.pipeline.publisher.settings") as mock_settings,
        patch("app.pipeline.publisher.resend") as mock_resend,
    ):
        mock_settings.resend_api_key = "re_test_key"
        mock_resend.Emails.send.side_effect = [
            {"id": "msg_1"},
            Exception("send failed"),
        ]
        result = await Publisher().send("<h1>Test</h1>", subscribers=subscribers)
    assert result["sent"] == 1
    assert result["failed"] == 1


@pytest.mark.asyncio
async def test_send_logs_delivery(subscribers):
    mock_db = MagicMock()
    with (
        patch("app.pipeline.publisher.settings") as mock_settings,
        patch("app.pipeline.publisher.resend") as mock_resend,
    ):
        mock_settings.resend_api_key = "re_test_key"
        mock_resend.Emails.send.return_value = {"id": "msg_1"}
        await Publisher().send(
            "<h1>Test</h1>",
            report_id=1,
            subscribers=subscribers,
            db=mock_db,
        )
    assert mock_db.add.call_count == 2
    assert mock_db.commit.call_count == 2


@pytest.mark.asyncio
async def test_send_empty_subscribers():
    with patch("app.pipeline.publisher.settings") as mock_settings:
        mock_settings.resend_api_key = "re_test_key"
        result = await Publisher().send("<h1>Test</h1>", subscribers=[])
    assert result["sent"] == 0
    assert result["failed"] == 0
