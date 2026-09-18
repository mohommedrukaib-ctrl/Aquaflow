"""
AquaFlow — Security Models
Powered by Quantum Axis
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class LoginAttempt(models.Model):
    """Track all login attempts for security monitoring."""

    STATUS_SUCCESS = 'success'
    STATUS_FAILED  = 'failed'
    STATUS_LOCKED  = 'locked'

    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED,  'Failed'),
        (STATUS_LOCKED,  'Locked (too many attempts)'),
    ]

    username    = models.CharField(max_length=150, db_index=True)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    user_agent  = models.TextField(blank=True)
    status      = models.CharField(
        max_length=20, choices=STATUS_CHOICES, db_index=True,
    )
    failure_reason = models.CharField(max_length=255, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'login_attempts'
        ordering = ['-timestamp']
        indexes  = [
            models.Index(fields=['username', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
        ]

    def __str__(self):
        return f'{self.username} ({self.status}) @ {self.timestamp}'

    @classmethod
    def record(cls, username, request, status, reason=''):
        ip = None
        ua = ''
        if request:
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT', '')[:500]
        return cls.objects.create(
            username=username, ip_address=ip, user_agent=ua,
            status=status, failure_reason=reason,
        )

    @classmethod
    def get_recent_failures(cls, username=None, ip_address=None, minutes=15):
        """Count failed attempts in last N minutes."""
        cutoff = timezone.now() - timedelta(minutes=minutes)
        qs = cls.objects.filter(
            status=cls.STATUS_FAILED,
            timestamp__gte=cutoff,
        )
        if username:
            qs = qs.filter(username=username)
        if ip_address:
            qs = qs.filter(ip_address=ip_address)
        return qs.count()


class AccountLockout(models.Model):
    """Track locked user accounts."""

    user       = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='lockout',
    )
    locked_at  = models.DateTimeField(auto_now_add=True)
    unlock_at  = models.DateTimeField()
    reason     = models.CharField(max_length=255, blank=True)
    unlocked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='unlocked_accounts',
    )
    unlocked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'account_lockouts'

    def __str__(self):
        return f'{self.user.username} — locked until {self.unlock_at}'

    def is_active(self):
        return (
            not self.unlocked_at and
            self.unlock_at > timezone.now()
        )

    @classmethod
    def lock_user(cls, user, minutes=30, reason='Too many failed attempts'):
        unlock_at = timezone.now() + timedelta(minutes=minutes)
        lockout, _ = cls.objects.update_or_create(
            user=user,
            defaults={
                'unlock_at':   unlock_at,
                'reason':      reason,
                'unlocked_at': None,
                'unlocked_by': None,
            },
        )
        return lockout

    @classmethod
    def is_user_locked(cls, user):
        try:
            lockout = cls.objects.get(user=user)
            return lockout.is_active()
        except cls.DoesNotExist:
            return False


class SecurityConfig(models.Model):
    """Single-row security configuration."""

    # Login security
    max_failed_attempts     = models.PositiveIntegerField(default=5)
    lockout_duration_minutes = models.PositiveIntegerField(default=30)
    failed_attempt_window   = models.PositiveIntegerField(default=15)

    # Session
    session_timeout_minutes = models.PositiveIntegerField(default=480)   # 8 hours
    idle_timeout_minutes    = models.PositiveIntegerField(default=60)    # 1 hour

    # Password
    min_password_length     = models.PositiveIntegerField(default=8)
    require_uppercase       = models.BooleanField(default=True)
    require_number          = models.BooleanField(default=True)
    require_special_char    = models.BooleanField(default=False)
    password_expiry_days    = models.PositiveIntegerField(default=0)     # 0 = never

    # HTTPS
    force_https             = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'security_config'

    def __str__(self):
        return 'Security Configuration'

    @classmethod
    def get_config(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj