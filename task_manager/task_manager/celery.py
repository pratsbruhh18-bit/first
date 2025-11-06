import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'task_manager.settings')

app = Celery('task_manager')

# Load custom settings from Django settings.py (using CELERY_ prefix)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django app configs
app.autodiscover_tasks()

# Timezone (make sure it matches your Django TIME_ZONE in settings.py)
app.conf.timezone = 'Asia/Kathmandu'

# Periodic schedule: run every hour at minute 0
app.conf.beat_schedule = {
    'send-due-soon-reminders-every-hour': {
        'task': 'tasks.tasks.send_due_soon_reminders',
        'schedule': crontab(minute=0, hour='*'),  # Every hour at :00
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
