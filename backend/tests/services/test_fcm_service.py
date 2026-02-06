import json
from unittest.mock import patch

import pytest

from app.services.fcm_service import FCM_MAX_DATA_BYTES, FCMService


@pytest.mark.anyio
async def test_oversized_payload_still_attempts_send():
    """FCMService should warn but still attempt to send oversized payloads."""
    with (
        patch.object(FCMService, "_initialized", True),
        patch("app.services.fcm_service.messaging") as mock_messaging,
    ):
        mock_messaging.send.return_value = "projects/test/messages/123"
        mock_messaging.Message = lambda **kwargs: kwargs

        oversized_payload = {
            "messages": json.dumps(
                [
                    {"message_id": f"id-{i}", "recipient": f"+1234567{i:04d}"}
                    for i in range(200)
                ]
            ),
            "body": "Test message",
        }

        result = await FCMService.send_sms_notification("fake-token", oversized_payload)
        assert result is True
        mock_messaging.send.assert_called_once()


@pytest.mark.anyio
async def test_accepts_small_payload():
    """FCMService should attempt to send payloads within the limit."""
    with (
        patch.object(FCMService, "_initialized", True),
        patch("app.services.fcm_service.messaging") as mock_messaging,
    ):
        mock_messaging.send.return_value = "projects/test/messages/123"
        mock_messaging.Message = lambda **kwargs: kwargs

        small_payload = {
            "messages": json.dumps(
                [{"message_id": "id-1", "recipient": "+1234567890"}]
            ),
            "body": "Hi",
        }

        # Verify it's actually under the limit
        data = {k: str(v) for k, v in small_payload.items()}
        assert len(json.dumps(data).encode("utf-8")) <= FCM_MAX_DATA_BYTES

        result = await FCMService.send_sms_notification("fake-token", small_payload)
        assert result is True
        mock_messaging.send.assert_called_once()
