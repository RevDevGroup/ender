# Celery config module
# Don't modify this!
import os
from dotenv import load_dotenv

load_dotenv(".env")

broker_url = os.environ["BROKER_URL"]
result_backend = os.environ["RESULT_BACKEND"]

task_compression = 'gzip'

task_annotations = {
    '*': {'rate_limit': os.environ["RATE_LIMIT"]}
}
