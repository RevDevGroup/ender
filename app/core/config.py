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

ANDROID_DEVICE = os.environ["ANDROID_DEVICE"]
