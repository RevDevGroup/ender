import os
import logging
from .celery_app import app
from app.mqtt.client import mqtt_client

logger = logging.getLogger(__name__)

ANDROID_DEVICE = os.environ["ANDROID_DEVICE"]

@app.task
def check_balance():
    raise NotImplementedError


@app.task(autoretry_for=([Exception]), retry_backoff=True)
def send_sms(phone: str, message_body: str, device_api_key: str = None) -> int:
    if device_api_key:
        # Enviar via MQTT
        message = f"{phone}:{message_body}"
        mqtt_client.publish_to_device(device_api_key, "sms", message)
        logger.info(f"SMS sent via MQTT to device {device_api_key}: {phone}")
        return 200  # Asumir éxito por ahora
    else:
        # Fallback a HTTP si no hay device_api_key
        import requests
        req = requests.post(
            ANDROID_DEVICE + "/message", json={"number": phone, "text": message_body}
        )
        return req.status_code


@app.task
def send_ussd():
    raise NotImplementedError
