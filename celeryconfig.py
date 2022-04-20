# Celery config module
# Don't modify this directly!
from dotenv import load_dotenv
from app.core.config import BROKER_URL_MAIN, RATE_LIMIT, RESULT_BACKEND

load_dotenv(".env")


broker_url = BROKER_URL_MAIN
result_backend = RESULT_BACKEND

task_compression = "gzip"

task_annotations = {"*": {"rate_limit": RATE_LIMIT}}

worker_cancel_long_running_tasks_on_connection_loss = True # Until Celery 6.0