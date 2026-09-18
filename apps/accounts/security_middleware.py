"""
AquaFlow — Security Middleware
Powered by Quantum Axis

- Idle session timeout
- Force logout after inactivity
"""

import logging
from django.contrib.auth import logout
from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger('apps')


class IdleTimeoutMiddleware:
    """
    Logs out users after configured idle time.
    Runs on every authenticated request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            self._check_idle_timeout(request)
        except Exception as e:
            logger.warning(f'Idle timeout check failed: {e}')

        return self.get_response(request)

    def _check_idle_timeout(self, request):
        if not request.user.is_authenticated:
            return

        # Skip static/media/API/AJAX to avoid interfering
        path = request.path
        if any(path.startswith(p) for p in ['/static/', '/media/', '/api/']):
            return

        try:
            from apps.accounts.security_models import SecurityConfig
            config = SecurityConfig.get_config()
        except Exception:
            return

        idle_minutes = config.idle_timeout_minutes
        if idle_minutes <= 0:
            return

        last_activity = request.session.get('last_activity')
        now = timezone.now()

        if last_activity:
            try:
                from datetime import datetime
                last_dt = datetime.fromisoformat(last_activity)
                # Ensure both timezone-aware
                if timezone.is_naive(last_dt):
                    last_dt = timezone.make_aware(last_dt)

                if (now - last_dt) > timedelta(minutes=idle_minutes):
                    username = request.user.username
                    logout(request)
                    messages.warning(
                        request,
                        f'You were logged out due to inactivity ({idle_minutes} minutes).'
                    )
                    logger.info(f'User {username} auto-logged out due to inactivity.')
            except Exception:
                pass

        # Update last activity
        request.session['last_activity'] = now.isoformat()