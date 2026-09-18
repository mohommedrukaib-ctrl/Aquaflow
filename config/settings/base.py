"""
AquaFlow Car Wash Management System
Base Settings — Shared across all environments
Powered by Quantum Axis
"""

import os
from pathlib import Path
import environ

# ─── Base Directory ───────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ─── Environment Variables ────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['127.0.0.1', 'localhost']),
    DB_PORT=(str, '5432'),
    DB_SSLMODE=(str, 'prefer'),
    TIMEZONE=(str, 'Asia/Colombo'),
    LANGUAGE_CODE=(str, 'en-us'),
    DEFAULT_CURRENCY_CODE=(str, 'LKR'),
    DEFAULT_CURRENCY_SYMBOL=(str, 'Rs.'),
    DEFAULT_CURRENCY_NAME=(str, 'Sri Lankan Rupee'),
    APP_VERSION=(str, '1.0.0'),
    REDIS_URL=(str, 'redis://127.0.0.1:6379/0'),
)

environ.Env.read_env(BASE_DIR / '.env')

# ─── Security ─────────────────────────────────────────────────
SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS')

# ─── Application Definition ───────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'channels',
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.businesses',
    'apps.branches',
    'apps.customers',
    'apps.vehicles',
    'apps.services',
    'apps.bookings',
    'apps.pos',
    'apps.orders',
    'apps.invoices',
    'apps.payments',
    'apps.wash',
    'apps.employees',
    'apps.inventory',
    'apps.suppliers',
    'apps.finance',
    'apps.memberships',
    'apps.loyalty',
    'apps.reports',
    'apps.backups',
    'apps.trash',
    'apps.audit',
    'apps.system',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ───────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
     'apps.backups.middleware.BackupScheduleMiddleware',
     'apps.accounts.security_middleware.IdleTimeoutMiddleware',  
]

# ─── URLs ─────────────────────────────────────────────────────
ROOT_URLCONF = 'config.urls'

# ─── Templates ────────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.system.context_processors.aquaflow_context',
            ],
        },
    },
]

# ─── WSGI / ASGI ─────────────────────────────────────────────
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ─── Database ─────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': env(
            'DB_ENGINE',
            default='django.db.backends.postgresql'
        ),
        'NAME': env('DB_NAME', default='aquaflow'),
        'USER': env('DB_USER', default='aquaflow_user'),
        'PASSWORD': env('DB_PASSWORD', default=''),
        'HOST': env('DB_HOST', default='127.0.0.1'),
        'PORT': env('DB_PORT', default='5432'),
        'OPTIONS': {
            'sslmode': env('DB_SSLMODE', default='prefer'),
        },
        'CONN_MAX_AGE': 60,
        'ATOMIC_REQUESTS': True,
    }
}

# ─── Password Validation ─────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': (
            'django.contrib.auth.password_validation'
            '.UserAttributeSimilarityValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation'
            '.MinimumLengthValidator'
        ),
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation'
            '.CommonPasswordValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation'
            '.NumericPasswordValidator'
        ),
    },
]

# ─── Internationalization ─────────────────────────────────────
LANGUAGE_CODE = env('LANGUAGE_CODE', default='en-us')
TIME_ZONE = env('TIMEZONE', default='Asia/Colombo')
USE_I18N = True
USE_TZ = True

# ─── Static Files ─────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
)

# ─── Media Files ─────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Default Primary Key ─────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Authentication ───────────────────────────────────────────
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ─── Sessions ─────────────────────────────────────────────────
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 28800        # 8 hours
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Needed for AJAX
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_NAME = 'aquaflow_session'

# ─── CSRF ─────────────────────────────────────────────────────
CSRF_COOKIE_NAME = 'aquaflow_csrftoken'

# ─── REST Framework ───────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': (
        'rest_framework.pagination.PageNumberPagination'
    ),
    'PAGE_SIZE': 25,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/minute',
        'user': '200/minute',
    },
}

# ─── CORS ─────────────────────────────────────────────────────
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = []

# ─── Channels (WebSocket) ────────────────────────────────────
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# ─── Celery ───────────────────────────────────────────────────
CELERY_BROKER_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = env(
    'REDIS_URL', default='redis://127.0.0.1:6379/0'
)
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

# ─── Logging ──────────────────────────────────────────────────
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': (
                '[{asctime}] [{levelname}] [{name}] {message}'
            ),
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'app_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'aquaflow.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'error.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'root': {
        'handlers': ['console', 'app_file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'app_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'app_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# ─── AquaFlow Application Constants ──────────────────────────
AQUAFLOW_VERSION = env('APP_VERSION', default='1.0.0')
AQUAFLOW_DEVELOPER = 'Quantum Axis'
AQUAFLOW_SYSTEM_NAME = 'AquaFlow'

# Currency defaults
DEFAULT_CURRENCY_CODE = env('DEFAULT_CURRENCY_CODE', default='LKR')
DEFAULT_CURRENCY_SYMBOL = env('DEFAULT_CURRENCY_SYMBOL', default='Rs.')
DEFAULT_CURRENCY_NAME = env(
    'DEFAULT_CURRENCY_NAME',
    default='Sri Lankan Rupee'
)

# Backup path
BACKUP_PATH = env(
    'BACKUP_PATH',
    default=str(BASE_DIR / 'backups')
)

# Print format options
PRINT_FORMATS = [
    ('thermal_80mm', 'Thermal Receipt (80mm)'),
    ('dot_matrix',   'Dot Matrix'),
    ('half_a4',      'Half A4'),
    ('a4',           'A4'),
]   

# ─── Cache ────────────────────────────────────────────────────
# Uses Redis if REDIS_URL is set, otherwise falls back to
# LocMemCache (safe for single-worker development only).
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
    }
}