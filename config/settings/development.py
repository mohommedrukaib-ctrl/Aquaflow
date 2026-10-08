"""
AquaFlow Development Settings
Powered by Quantum Axis
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ['*']

# ─── Debug Toolbar ────────────────────────────────────────────
INSTALLED_APPS += ['debug_toolbar']  # noqa: F405

MIDDLEWARE = [  # noqa: F405
    'debug_toolbar.middleware.DebugToolbarMiddleware',
] + MIDDLEWARE  # noqa: F405

INTERNAL_IPS = ['127.0.0.1', '::1']

# ─── Relaxed Password Validation in Dev ───────────────────────
AUTH_PASSWORD_VALIDATORS = []

# ─── Email to Console ─────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ─── No HTTPS Requirement in Dev ──────────────────────────────
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# ─── In-Memory Channel Layer (no Redis needed in dev) ─────────
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}