"""
AquaFlow — Customer Model
Powered by Quantum Axis

One customer may own multiple vehicles.
Soft delete — never physically delete customers
with financial history.
"""

from django.db import models
from django.contrib.auth.models import User
from django.db import connection


def generate_customer_code():
    """
    Concurrency-safe customer code using PostgreSQL sequence.
    Returns: CUS-00001
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('customer_code_seq')")
        seq = cursor.fetchone()[0]
    return f'CUS-{seq:05d}'


class Customer(models.Model):

    STATUS_ACTIVE   = 'active'
    STATUS_INACTIVE = 'inactive'

    STATUS_CHOICES = [
        (STATUS_ACTIVE,   'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]

    # ─── Identity ─────────────────────────────────────────────
    customer_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text='Auto-generated. Example: CUS-00001',
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.PROTECT,
        related_name='customers',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='customers',
        null=True,
        blank=True,
    )

    # ─── Personal Info ────────────────────────────────────────
    name  = models.CharField(
        max_length=255,
        db_index=True,
    )
    phone = models.CharField(
        max_length=50,
        db_index=True,
        blank=True,
    )
    phone2 = models.CharField(
        max_length=50,
        blank=True,
    )
    email   = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes   = models.TextField(blank=True)

    # ─── Loyalty Points ───────────────────────────────────────
    loyalty_points = models.IntegerField(default=0)

    # ─── Status ───────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
    )

    # ─── Soft Delete ──────────────────────────────────────────
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_customers',
    )

    # ─── Timestamps ───────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_customers',
    )

    # ─── Managers ─────────────────────────────────────────────
    objects     = models.Manager()  # default — all records

    class Meta:
        db_table            = 'customers'
        verbose_name        = 'Customer'
        verbose_name_plural = 'Customers'
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['phone']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.name} ({self.customer_code})'

    def save(self, *args, **kwargs):
        if not self.customer_code:
            self.customer_code = generate_customer_code()
        if not self.business_id:
            from apps.businesses.models import Business
            self.business = Business.objects.get(pk=1)
        super().save(*args, **kwargs)

    def soft_delete(self, user=None):
        """
        Soft delete — marks as deleted.
        Never physically removes from database.
        """
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=[
            'is_deleted', 'deleted_at', 'deleted_by'
        ])

    def restore(self):
        """Restore from soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=[
            'is_deleted', 'deleted_at', 'deleted_by'
        ])

    @property
    def vehicle_count(self):
        return self.vehicles.filter(is_deleted=False).count()

    @property
    def display_phone(self):
        return self.phone or self.phone2 or '—'