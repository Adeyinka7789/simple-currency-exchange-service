import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
# 'core.settings' is the path to your settings file.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Initialize a Celery application instance
app = Celery('core')

# Load task configurations from Django settings.
# The configuration object is CELERY_... in settings.py.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover task modules (tasks.py) in all installed apps.
app.autodiscover_tasks()

# Example: Task for debugging/verification
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')