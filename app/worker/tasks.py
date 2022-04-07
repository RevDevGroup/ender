from .celery_app import app

@app.task
def check_balance():
    raise NotImplementedError

@app.task
def send_sms():
    pass

@app.task
def send_ussd():
    raise NotImplementedError