"""
AquaFlow — Branch Model
Powered by Quantum Axis

Supports multiple branches per business.
V1 ships with a single default branch.
"""

from django.db import models


class Branch(models.Model):

    STATUS_ACTIVE   = 'active'
    STATUS_INACTIVE = 'inactive'

    STATUS_CHOICES = [
        (STATUS_ACTIVE,   'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]

    # ─── Identity ─────────────────────────────────────────────
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.PROTECT,
        related_name='branches',
    )
    name = models.CharField(max_length=255)
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text='Short unique code. Example: MAIN, BR01, CITY',
    )

    # ─── Contact ──────────────────────────────────────────────
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city          = models.CharField(max_length=100, blank=True)
    phone         = models.CharField(max_length=50,  blank=True)
    email         = models.EmailField(blank=True)

    # ─── Status ───────────────────────────────────────────────
    status     = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )
    is_default = models.BooleanField(
        default=False,
        help_text='The default branch for new records.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'branches'
        verbose_name        = 'Branch'
        verbose_name_plural = 'Branches'
        ordering            = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'

    @classmethod
    def get_default(cls):
        """Returns the default branch."""
        return cls.objects.filter(is_default=True).first()