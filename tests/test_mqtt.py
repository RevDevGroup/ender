import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Mock config before importing
sys.modules['app.core.config'] = MagicMock()
sys.modules['app.models.models'] = MagicMock()

# Patch the constants
with patch('app.mqtt.client.MQTT_USERNAME', ''), \
     patch('app.mqtt.client.MQTT_PASSWORD', ''), \
     patch('app.mqtt.client.MQTT_TLS_CERT', ''), \
     patch('app.mqtt.client.MQTT_TLS_KEY', ''), \
     patch('app.mqtt.client.MQTT_CA_CERT', ''):
    from app.mqtt.client import MQTTClient


@pytest.mark.asyncio
async def test_mqtt_auth_valid_key():
    client = MQTTClient()
    client.client = MagicMock()

    # Mock valid API key
    with patch('app.mqtt.client.ApiKey') as mock_api_key:
        mock_instance = MagicMock()
        mock_api_key.get_or_none.return_value = mock_instance

        await client.handle_auth("valid_key", "client_123")

        client.client.publish.assert_called_with("server/auth/valid_key", "authenticated")
        assert "valid_key" in client.connected_devices


@pytest.mark.asyncio
async def test_mqtt_auth_invalid_key():
    client = MQTTClient()
    client.client = MagicMock()

    # Mock invalid API key
    with patch('app.mqtt.client.ApiKey') as mock_api_key:
        mock_api_key.get_or_none.return_value = None

        await client.handle_auth("invalid_key", "client_123")

        client.client.publish.assert_called_with("server/auth/invalid_key", "unauthorized")
        assert "invalid_key" not in client.connected_devices


def test_mqtt_publish_to_device():
    client = MQTTClient()
    client.connected_devices = {"api_key": "client_123"}
    client.client = MagicMock()

    client.publish_to_device("api_key", "test_topic", "test_message")

    client.client.publish.assert_called_with("devices/api_key/test_topic", "test_message", qos=1)


def test_mqtt_publish_to_disconnected_device():
    client = MQTTClient()
    client.client = MagicMock()

    with patch('app.mqtt.client.logger') as mock_logger:
        client.publish_to_device("disconnected_key", "test_topic", "test_message")

        mock_logger.error.assert_called_with("Device disconnected_key not connected")