# Celery config module
# Don't modify this directly!
from app.core.config import BROKER_URL_MAIN, RATE_LIMIT, RESULT_BACKEND

broker_url = BROKER_URL_MAIN
result_backend = RESULT_BACKEND

task_compression = "gzip"

task_annotations = {"*": {"rate_limit": RATE_LIMIT}}
