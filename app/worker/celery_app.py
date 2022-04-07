from celery import Celery

app = Celery('ender', include=['app.worker.tasks'])
app.config_from_object('celeryconfig')

if __name__ == '__main__':
    app.start()