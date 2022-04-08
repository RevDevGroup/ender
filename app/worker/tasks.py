import requests

from app.core.config import ANDROID_DEVICE

from .celery_app import app


@app.task
def check_balance():
    raise NotImplementedError


@app.task(autoretry_for=([requests.exceptions.RequestException]), retry_backoff=True)
def send_sms(phone: str, message_body: str) -> int:
    req = requests.post(
        ANDROID_DEVICE + "/message", json={"number": phone, "text": message_body}
    )
    return req.status_code


@app.task
def send_ussd():
    raise NotImplementedError
