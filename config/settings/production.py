"""
AquaFlow Production Settings
Powered by Quantum Axis
"""

from .base import *  # noqa: F401, F403

DEBUG = False

# ─── Security Headers ─────────────────────────────────────────
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ─── Redis Channel Layer for Production ───────────────────────
import environ  # noqa: E402
env = environ.Env()

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [env('REDIS_URL', default='redis://127.0.0.1:6379/0')],
        },
    },
}