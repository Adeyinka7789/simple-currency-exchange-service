import os
from pathlib import Path
from decouple import config, Csv
from decimal import Decimal
import dj_database_url  # CRITICAL: Used to correctly parse the DATABASE_URL string

# ---------------------------------------------
# BASE DIRECTORY
# ---------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------
# SECURITY & ENVIRONMENT SETTINGS
# ---------------------------------------------
SECRET_KEY = config('SECRET_KEY', default='django-insecure-placeholder-key-for-dev')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())

# ---------------------------------------------
# APPLICATION DEFINITION
# ---------------------------------------------
INSTALLED_APPS = [
    # Core Django Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 3rd Party Apps
    'corsheaders',
    'rest_framework',
    'django_celery_beat',   # For database-backed task scheduling
    # Custom Apps
    'exchange_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ---------------------------------------------
# DATABASE CONFIGURATION (PostgreSQL-ready)
# ---------------------------------------------
DATABASES = {
    'default': dj_database_url.parse(
        config(
            'DATABASE_URL',
            default=f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}"
        )
    )
}

# ---------------------------------------------
# CACHING (Redis)
# ---------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'ces_cache',
    }
}

# ---------------------------------------------
# CELERY CONFIGURATION
# ---------------------------------------------
CELERY_BROKER_URL = config('REDIS_URL', default='redis://127.0.0.1:6379/1')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://127.0.0.1:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Lagos'

# Celery Beat Settings (managed dynamically through Admin)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ---------------------------------------------
# PASSWORD VALIDATION
# ---------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------
# INTERNATIONALIZATION
# ---------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------
# STATIC FILES
# ---------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------
# REST FRAMEWORK SETTINGS
# ---------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

# ---------------------------------------------
# CUSTOM BUSINESS LOGIC SETTINGS
# ---------------------------------------------
CONVERSION_MARGIN = config('CONVERSION_MARGIN', default=Decimal('0.005'), cast=Decimal)
FX_API_KEY = config('FX_API_KEY', default='default-test-key')

# FIX: Changed the default domain to the most reliable free-tier Fixer endpoint.
# The endpoint ('/latest') will be added by the API client, so we must only provide the base URL here.
FX_API_BASE_URL = config('FX_API_BASE_URL', default='https://exchangesrateapi.com/api')
FX_PROVIDER_NAME = config('FX_PROVIDER_NAME', default='ExchangesRateAPI')

# REQUIRED FOR CORS
CORS_ALLOW_ALL_ORIGINS = True # Allow all origins for local development simplicity
# OR, more securely, specify the origins (e.g., if you run the HTML on a different port):
# CORS_ALLOWED_ORIGINS = [
#     "http://127.0.0.1:8000",
#     "http://localhost:8000",
# ]