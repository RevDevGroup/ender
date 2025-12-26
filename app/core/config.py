import os

from dotenv import load_dotenv

load_dotenv("./.env")

# DB config.
DATABASE_URL = os.environ["DATABASE_URL"]

# App config.

# To get a string like this run:
# openssl rand -hex 32
API_SECRET_KEY = os.environ["API_SECRET_KEY"]

# Celery config.
BROKER_URL_MAIN = os.environ["BROKER_URL"]
RESULT_BACKEND = os.environ["RESULT_BACKEND"]
RATE_LIMIT = os.environ["RATE_LIMIT"]

# MQTT config.
MQTT_BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", 8883))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")
MQTT_TLS_CERT = os.environ.get("MQTT_TLS_CERT", "")
MQTT_TLS_KEY = os.environ.get("MQTT_TLS_KEY", "")
MQTT_CA_CERT = os.environ.get("MQTT_CA_CERT", "")
