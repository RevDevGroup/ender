import paho.mqtt.client as mqtt
import ssl
import logging
import os
from typing import Callable, Dict
from app.core.config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    MQTT_TLS_CERT,
    MQTT_TLS_KEY,
    MQTT_CA_CERT,
)
from app.models.models import ApiKey

logger = logging.getLogger(__name__)

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        # Configurar TLS solo si hay certificados y existen los archivos
        if (MQTT_TLS_CERT and MQTT_TLS_KEY and MQTT_CA_CERT and
            os.path.exists(MQTT_TLS_CERT) and os.path.exists(MQTT_TLS_KEY) and os.path.exists(MQTT_CA_CERT)):
            self.client.tls_set(
                ca_certs=MQTT_CA_CERT,
                certfile=MQTT_TLS_CERT,
                keyfile=MQTT_TLS_KEY,
                tls_version=ssl.PROTOCOL_TLS,
            )
            self.client.tls_insecure_set(False)

        self.connected_devices: Dict[str, str] = {}  # api_key -> client_id
        self.message_handlers: Dict[str, Callable] = {}

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker")
            # Suscribirse a topics de autenticación y mensajes
            client.subscribe("devices/auth/+")
            client.subscribe("devices/messages/+")
        else:
            logger.error(f"Failed to connect, return code {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        logger.info(f"Received message on {topic}: {payload}")

        if topic.startswith("devices/auth/"):
            api_key = topic.split("/")[-1]
            self.handle_auth(api_key, payload)
        elif topic.startswith("devices/messages/"):
            api_key = topic.split("/")[-1]
            self.handle_message(api_key, payload)

    def on_disconnect(self, client, userdata, rc):
        logger.info("Disconnected from MQTT Broker")

    async def handle_auth(self, api_key: str, client_id: str):
        # Validar API key
        api_key_obj = await ApiKey.get_or_none(key=api_key, is_active=True)
        if api_key_obj:
            self.connected_devices[api_key] = client_id
            # Publicar confirmación
            self.client.publish(f"server/auth/{api_key}", "authenticated")
            logger.info(f"Device {client_id} authenticated with API key {api_key}")
        else:
            self.client.publish(f"server/auth/{api_key}", "unauthorized")
            logger.warning(f"Unauthorized access attempt with API key {api_key}")

    async def handle_message(self, api_key: str, message: str):
        if api_key in self.connected_devices:
            # Procesar mensaje, por ejemplo, enviar SMS via Celery
            # Aquí podríamos llamar a una función para procesar
            logger.info(f"Processing message from {api_key}: {message}")
            # Llamar a handler si existe
            if api_key in self.message_handlers:
                await self.message_handlers[api_key](message)
        else:
            logger.warning(f"Message from unauthorized device {api_key}")

    def publish_to_device(self, api_key: str, topic: str, message: str, qos=1):
        if api_key in self.connected_devices:
            full_topic = f"devices/{api_key}/{topic}"
            self.client.publish(full_topic, message, qos=qos)
        else:
            logger.error(f"Device {api_key} not connected")

    def start(self):
        self.client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

# Instancia global
mqtt_client = MQTTClient()