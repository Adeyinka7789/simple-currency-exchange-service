import os
from pathlib import Path
from decouple import config, Csv
from decimal import Decimal

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# go the APi key here: https://console.fastforex.io/api-keys/listing#

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# --- SECURITY & ENVIRONMENT CONFIGURATION ---
# SECRET_KEY, DEBUG, and ALLOWED_HOSTS MUST be pulled from environment variables.
SECRET_KEY = config('SECRET_KEY', default='django-insecure-z!x-placeholder-key-for-dev-98$!0')

# WARNING: Set DEBUG=False and allowed hosts in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())


# Application definition

INSTALLED_APPS = [
    # Core Django Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 3rd Party Apps required for the project
    'rest_framework',        # For our API endpoints (DRF)
    'django_celery_beat',    # For database-backed scheduling (Celery Beat)
    
    # My Apps
    'exchange_app',          # The core application for FX logic
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsfViewMiddleware',
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
                'django.template.context_processors.debug', # Added debug context processor
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# --- DATABASE CONFIGURATION (PostgreSQL) ---
# Uses the DATABASE_URL environment variable for production readiness
DATABASES = {
    'default': config(
        'DATABASE_URL',
        default='sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3'),
        # In a real environment, this ensures Django uses the configured PostgreSQL connection
        engine='django.db.backends.postgresql'
    )
}

# --- CACHING CONFIGURATION (Redis) ---
# CRITICAL for the Low-Latency Read NFR. Uses Redis as the primary cache backend.
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'ces_cache' # Unique prefix to prevent key collision
    }
}


# --- CELERY CONFIGURATION (Asynchronous Resilience) ---
# Celery must use the same Redis instance as the cache broker.
CELERY_BROKER_URL = config('REDIS_URL', default='redis://127.0.0.1:6379/1')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://127.0.0.1:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Lagos' # Ensure all scheduled tasks align with local time

# CELERY BEAT SETUP
# We use django-celery-beat for dynamic scheduling via the Admin interface.
# The actual schedule (e.g., hourly) will be configured in the Django Admin.


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Lagos' # Set to your local timezone for proper audit logging

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- REST FRAMEWORK CONFIGURATION ---
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny', # Allow access for initial testing
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    # Ensure high-precision numbers are serialized correctly
    'NUM_PRECISION': 8, 
}


# --- APPLICATION SPECIFIC SETTINGS ---
# Define core business constants, pulled from environment variables for easy modification
# CONVERSION_MARGIN must be cast to Decimal for financial accuracy
CONVERSION_MARGIN = config('CONVERSION_MARGIN', default=Decimal('0.005'), cast=Decimal)

# External API Configuration (Key must be secured)
FX_API_KEY = config('FX_API_KEY', default='default-test-key') 
FX_API_BASE_URL = config('FX_API_BASE_URL', default='https://api.exchangeratesapi.io/latest')