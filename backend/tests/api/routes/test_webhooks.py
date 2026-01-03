import json

from fastapi.testclient import TestClient

from app.models import WebhookConfigCreate, WebhookConfigUpdate


def test_create_webhook(
    client: TestClient,
    superuser_token_headers: dict[str, str],
):
    """Test creating a webhook"""
    webhook_in = WebhookConfigCreate(
        url="https://example.com/webhook",
        events=json.dumps(["sms_received", "sms_sent"]),
        active=True,
    )

    response = client.post(
        "/api/v1/webhooks",
        headers=superuser_token_headers,
        json=webhook_in.model_dump(),
    )

    assert response.status_code == 201
    assert response.json()["success"] is True
    assert "data" in response.json()


def test_list_webhooks(
    client: TestClient,
    superuser_token_headers: dict[str, str],
):
    """Test listing webhooks"""
    response = client.get(
        "/api/v1/webhooks",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "data" in response.json()


def test_get_webhook(
    client: TestClient,
    superuser_token_headers: dict[str, str],
):
    """Test getting a specific webhook"""
    # First create a webhook
    webhook_in = WebhookConfigCreate(
        url="https://example.com/webhook",
        events=json.dumps(["sms_received"]),
        active=True,
    )

    create_response = client.post(
        "/api/v1/webhooks",
        headers=superuser_token_headers,
        json=webhook_in.model_dump(),
    )
    webhook_id = create_response.json()["data"]["id"]

    # Now get it
    response = client.get(
        f"/api/v1/webhooks/{webhook_id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["id"] == webhook_id


def test_update_webhook(
    client: TestClient,
    superuser_token_headers: dict[str, str],
):
    """Test updating a webhook"""
    # First create a webhook
    webhook_in = WebhookConfigCreate(
        url="https://example.com/webhook",
        events=json.dumps(["sms_received"]),
        active=True,
    )

    create_response = client.post(
        "/api/v1/webhooks",
        headers=superuser_token_headers,
        json=webhook_in.model_dump(),
    )
    webhook_id = create_response.json()["data"]["id"]

    # Update it
    update_in = WebhookConfigUpdate(
        url="https://example.com/updated-webhook",
        events=json.dumps(["sms_received", "sms_sent"]),
        active=False,
    )

    response = client.put(
        f"/api/v1/webhooks/{webhook_id}",
        headers=superuser_token_headers,
        json=update_in.model_dump(),
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["url"] == "https://example.com/updated-webhook"


def test_delete_webhook(
    client: TestClient,
    superuser_token_headers: dict[str, str],
):
    """Test deleting a webhook"""
    # First create a webhook
    webhook_in = WebhookConfigCreate(
        url="https://example.com/webhook",
        events=json.dumps(["sms_received"]),
        active=True,
    )

    create_response = client.post(
        "/api/v1/webhooks",
        headers=superuser_token_headers,
        json=webhook_in.model_dump(),
    )
    webhook_id = create_response.json()["data"]["id"]

    # Delete it
    response = client.delete(
        f"/api/v1/webhooks/{webhook_id}",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Webhook deleted"
