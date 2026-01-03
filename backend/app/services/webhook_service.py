import hashlib
import hmac
import json
from typing import Any

import httpx

from app.models import SMSMessage, WebhookConfig


class WebhookService:
    """Servicio para enviar webhooks HTTP"""

    @staticmethod
    async def send_webhook(
        webhook: WebhookConfig, message: SMSMessage, timeout: int = 10
    ) -> dict[str, Any]:
        """Enviar webhook HTTP con mensaje SMS"""
        if not webhook.active:
            return {"success": False, "error": "Webhook inactivo"}

        # Preparar payload
        payload = {
            "event": "sms_received",
            "from": message.from_number or "",
            "body": message.body,
            "timestamp": message.created_at.isoformat() if message.created_at else None,
            "message_id": str(message.id),
        }

        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

        # Preparar headers
        headers = {"Content-Type": "application/json"}

        # Agregar firma HMAC si existe secret_key
        if webhook.secret_key:
            signature = WebhookService._generate_signature(
                webhook.secret_key, json.dumps(payload_json)
            )
            headers["X-Webhook-Signature"] = signature

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(webhook.url, json=payload, headers=headers)
                response.raise_for_status()

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response": response.text,
                }
        except httpx.TimeoutException:
            return {"success": False, "error": "Timeout al enviar webhook"}
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"Error HTTP {e.response.status_code}",
                "status_code": e.response.status_code,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def _generate_signature(secret_key: str, payload: str) -> str:
        """Generar firma HMAC-SHA256"""
        return hmac.new(
            secret_key.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify_signature(secret_key: str, payload: str, signature: str) -> bool:
        """Verificar firma HMAC"""
        expected_signature = WebhookService._generate_signature(secret_key, payload)
        return hmac.compare_digest(expected_signature, signature)
