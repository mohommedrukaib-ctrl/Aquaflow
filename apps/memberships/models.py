"""
AquaFlow — Membership Models
Powered by Quantum Axis
"""

from django.db import models, connection
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta


class MembershipPlan(models.Model):
    """Defines the packages you sell (e.g., 10 washes for Rs. 15,000)."""

    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price       = models.DecimalField(max_digits=12, decimal_places=2)
    duration_days = models.PositiveIntegerField(
        default=365,
        help_text='Validity in days.',
    )
    wash_count  = models.PositiveIntegerField(
        default=10,
        help_text='Number of washes included. 0 = unlimited.',
    )
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Discount on non-included services.',
    )
    color = models.CharField(
        max_length=20, default='#04a9f5',
        help_text='Display color for this plan.',
    )
    is_active  = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'membership_plans'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Membership(models.Model):

    STATUS_ACTIVE    = 'active'
    STATUS_EXPIRED   = 'expired'
    STATUS_CANCELLED = 'cancelled'
    STATUS_SUSPENDED = 'suspended'

    STATUS_CHOICES = [
        (STATUS_ACTIVE,    'Active'),
        (STATUS_EXPIRED,   'Expired'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_SUSPENDED, 'Suspended'),
    ]

    membership_number = models.CharField(
        max_length=30, unique=True, editable=False,
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='memberships',
    )
    plan = models.ForeignKey(
        MembershipPlan,
        on_delete=models.PROTECT,
        related_name='memberships',
    )

    start_date  = models.DateField()
    expiry_date = models.DateField(db_index=True)

    wash_count_total     = models.PositiveIntegerField(default=0)
    wash_count_used      = models.PositiveIntegerField(default=0)
    wash_count_remaining = models.PositiveIntegerField(default=0)

    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_ACTIVE, db_index=True,
    )
    notes  = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_memberships',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'memberships'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.membership_number} — {self.customer.name}'

    def save(self, *args, **kwargs):
        if not self.membership_number:
            with connection.cursor() as cursor:
                cursor.execute("SELECT nextval('membership_number_seq')")
                num = cursor.fetchone()[0]
            self.membership_number = f'MEM-{num:06d}'

        if not self.expiry_date and self.plan:
            self.expiry_date = self.start_date + timedelta(days=self.plan.duration_days)

        if not self.wash_count_total and self.plan:
            self.wash_count_total = self.plan.wash_count
            self.wash_count_remaining = self.plan.wash_count

        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return (
            self.status == self.STATUS_ACTIVE and
            self.expiry_date >= timezone.now().date()
        )

    @property
    def days_remaining(self):
        if not self.expiry_date:
            return 0
        delta = self.expiry_date - timezone.now().date()
        return max(0, delta.days)

    def use_wash(self, count=1):
        """Deduct washes from membership."""
        if self.wash_count_total == 0:
            return True  # Unlimited
        if self.wash_count_remaining >= count:
            self.wash_count_used += count
            self.wash_count_remaining -= count
            self.save(update_fields=[
                'wash_count_used', 'wash_count_remaining', 'updated_at'
            ])
            return True
        return False