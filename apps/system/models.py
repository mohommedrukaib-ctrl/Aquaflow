"""
AquaFlow — System Models
Powered by Quantum Axis
"""

from django.db import models
from django.contrib.auth.models import User
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib


def get_encryption_key():
    """Derive a Fernet key from SECRET_KEY."""
    secret = settings.SECRET_KEY.encode('utf-8')
    key = hashlib.sha256(secret).digest()
    return base64.urlsafe_b64encode(key)


def encrypt_value(value):
    """Encrypt a string using Fernet."""
    if not value:
        return ''
    f = Fernet(get_encryption_key())
    return f.encrypt(value.encode('utf-8')).decode('utf-8')


def decrypt_value(encrypted):
    """Decrypt a Fernet-encrypted string."""
    if not encrypted:
        return ''
    try:
        f = Fernet(get_encryption_key())
        return f.decrypt(encrypted.encode('utf-8')).decode('utf-8')
    except Exception:
        return ''


# ─── System Settings ──────────────────────────────────────────
class SystemSetting(models.Model):
    """Key-value store for system configuration."""

    key         = models.CharField(max_length=100, unique=True)
    value       = models.TextField(blank=True)
    description = models.TextField(blank=True)
    is_sensitive = models.BooleanField(default=False)
    updated_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
    )
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'system_settings'
        verbose_name        = 'System Setting'
        verbose_name_plural = 'System Settings'
        ordering            = ['key']

    def __str__(self):
        return self.key

    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value, user=None, description=''):
        obj, _ = cls.objects.get_or_create(key=key)
        obj.value = value
        obj.updated_by = user
        if description:
            obj.description = description
        obj.save()
        return obj

# ─── Audit Log ────────────────────────────────────────────────

class AuditLog(models.Model):
    """Immutable audit trail."""

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_logs',
    )
    user_name_snapshot = models.CharField(max_length=255, blank=True)

    action      = models.CharField(max_length=100, db_index=True)
    module      = models.CharField(max_length=100, db_index=True)
    object_type = models.CharField(max_length=100, blank=True)
    object_id   = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)

    previous_data = models.JSONField(null=True, blank=True)
    new_data      = models.JSONField(null=True, blank=True)

    ip_address    = models.GenericIPAddressField(null=True, blank=True)
    user_agent    = models.TextField(blank=True)

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table            = 'audit_logs'
        verbose_name        = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering            = ['-timestamp']

    def __str__(self):
        return f'[{self.timestamp}] {self.user_name_snapshot} — {self.action}'

    @classmethod
    def log(cls, action, module, user=None, object_type='',
            object_id='', object_repr='', previous_data=None,
            new_data=None, ip_address=None, user_agent=''):
        """Convenience method — never logs passwords."""
        user_name = ''
        if user:
            user_name = user.get_full_name() or user.username

        return cls.objects.create(
            user=user, user_name_snapshot=user_name,
            action=action, module=module,
            object_type=object_type, object_id=str(object_id),
            object_repr=object_repr,
            previous_data=previous_data, new_data=new_data,
            ip_address=ip_address, user_agent=user_agent,
        )


# ─── Database Configuration ───────────────────────────────────

class DatabaseConfig(models.Model):
    """
    Encrypted database connection configuration.
    Only Super Admin can view/edit.
    Password is Fernet-encrypted.
    """

    SSL_DISABLE  = 'disable'
    SSL_ALLOW    = 'allow'
    SSL_PREFER   = 'prefer'
    SSL_REQUIRE  = 'require'
    SSL_VERIFY_CA   = 'verify-ca'
    SSL_VERIFY_FULL = 'verify-full'

    SSL_CHOICES = [
        (SSL_DISABLE,     'Disable'),
        (SSL_ALLOW,       'Allow'),
        (SSL_PREFER,      'Prefer (default)'),
        (SSL_REQUIRE,     'Require'),
        (SSL_VERIFY_CA,   'Verify CA'),
        (SSL_VERIFY_FULL, 'Verify Full'),
    ]

    engine = models.CharField(
        max_length=100,
        default='django.db.backends.postgresql',
    )
    host     = models.CharField(max_length=255, default='127.0.0.1')
    port     = models.CharField(max_length=10, default='5432')
    db_name  = models.CharField(max_length=255)
    username = models.CharField(max_length=255)

    # Encrypted password — never returned in API/UI
    password_encrypted = models.TextField(blank=True)

    ssl_mode = models.CharField(
        max_length=20, choices=SSL_CHOICES, default=SSL_PREFER,
    )

    is_active           = models.BooleanField(default=False)
    is_last_known_good  = models.BooleanField(default=False)

    tested_at    = models.DateTimeField(null=True, blank=True)
    test_result  = models.CharField(max_length=255, blank=True)

    applied_at   = models.DateTimeField(null=True, blank=True)
    applied_by   = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='db_configs_applied',
    )

    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'db_configs'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.username}@{self.host}:{self.port}/{self.db_name}'

    def set_password(self, plain_password):
        """Encrypt and store password."""
        self.password_encrypted = encrypt_value(plain_password)

    def get_password(self):
        """Decrypt password (used internally only)."""
        return decrypt_value(self.password_encrypted)

    def to_env_dict(self):
        """Convert to dict suitable for .env file."""
        return {
            'DB_ENGINE':   self.engine,
            'DB_HOST':     self.host,
            'DB_PORT':     self.port,
            'DB_NAME':     self.db_name,
            'DB_USER':     self.username,
            'DB_PASSWORD': self.get_password(),
            'DB_SSLMODE':  self.ssl_mode,
        }