import uuid

from fastapi.testclient import TestClient

from app.models import SMSDeviceCreate, SMSMessageCreate


def test_send_sms_with_invalid_device(
    client: TestClient,
    superuser_token_headers: dict[str, str],
):
    """Test sending SMS with non-existent device should fail"""
    # Send SMS with invalid device
    message_in = SMSMessageCreate(
        to="+1234567890",
        body="Test message",
        device_id=uuid.uuid4(),  # ID that does not exist
    )

    response = client.post(
        "/api/v1/sms/send",
        headers=superuser_token_headers,
        json=message_in.model_dump(mode="json"),
    )

    assert response.status_code == 400
    assert "Device with id" in response.json()["detail"]


def test_send_sms_with_wrong_user_device(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
):
    """Test sending SMS with device from another user should fail"""
    # Create device for normal user
    device_in = SMSDeviceCreate(name="Test Device", phone_number="+1234567890")
    response = client.post(
        "/api/v1/sms/devices",
        headers=normal_user_token_headers,
        json=device_in.model_dump(),
    )
    device_id = response.json()["data"]["device_id"]

    # Try to use that device with the superuser
    message_in = SMSMessageCreate(
        to="+1234567890", body="Test message", device_id=uuid.UUID(device_id)
    )

    response = client.post(
        "/api/v1/sms/send",
        headers=superuser_token_headers,
        json=message_in.model_dump(mode="json"),
    )

    assert response.status_code == 400
    assert "does not belong to user" in response.json()["detail"]


def test_send_bulk_sms_with_invalid_device(
    client: TestClient,
    superuser_token_headers: dict[str, str],
):
    """Test sending bulk SMS with non-existent device should fail"""
    bulk_in = {
        "recipients": ["+1234567890", "+0987654321"],
        "body": "Test bulk message",
        "device_id": str(uuid.uuid4()),  # ID que no existe
    }

    response = client.post(
        "/api/v1/sms/send-bulk", headers=superuser_token_headers, json=bulk_in
    )

    assert response.status_code == 400
    assert "Device with id" in response.json()["detail"]
