import os
from celery import Celery
from celery.schedules import crontab


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "heartbeat-every-minute": {
        "task": "courses.tasks.heartbeat",
        "schedule": crontab(),  # раз в минуту
    },
# ежедневная деактивация
    "deactivate-inactive-users-daily": {
        "task": "users.tasks.deactivate_inactive_users",
        "schedule": crontab(hour=3, minute=0),  # каждый день в 03:00 локального времени
    },
}