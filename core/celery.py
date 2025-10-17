import os

from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
# This ensures Celery knows which settings to load.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Create a Celery application instance.
# We use the name 'core' (the Django project name) for simplicity, 
# matching the core project directory name.
app = Celery('core')

# Configure Celery using the Django settings.
# The 'CELERY_' prefix in settings.py is used here (e.g., CELERY_BROKER_URL).
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
# Using 'lambda: settings.INSTALLED_APPS' explicitly tells Celery where to look 
# for 'tasks.py' files, ensuring robust discovery.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    """A debug task to confirm Celery is running correctly."""
    # The 'self' argument provides access to the task instance, including retries.
    print(f'Request: {self.request!r}')

# Note: This is the bootstrap file. The actual rate ingestion schedule (FR1.1) 
# will be managed dynamically via the database using django-celery-beat.