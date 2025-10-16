# --- CES Project Setup Script ---

# 1. Create the main project directory and virtual environment
mkdir ces_project
cd ces_project
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# 2. Install core dependencies (based on requirements.txt)
# Note: psycopg2, redis, and django-celery-beat are critical
pip install Django djangorestframework psycopg2-binary python-decouple celery redis django-redis django-celery-beat requests

# 3. Create the Django project and the core app
django-admin startproject core .
python manage.py startapp exchange_app

# 4. Create the initial settings file and manage.py (for completeness)
# You will need to manually edit the settings later to reflect the files below.

echo "--- Setup Complete ---"
echo "Next steps: Replace core/settings.py with the file provided below and start infra with Docker."