"""
AquaFlow — Order Model
Powered by Quantum Axis
"""

from django.db import models, connection
from django.contrib.auth.models import User
from decimal import Decimal


class Order(models.Model):

    STATUS_DRAFT     = 'draft'
    STATUS_COMPLETED = 'completed'
    STATUS_VOID      = 'void'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_DRAFT,     'Draft'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_VOID,      'Void'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    PAYMENT_PENDING = 'pending'
    PAYMENT_PARTIAL = 'partial'
    PAYMENT_PAID    = 'paid'
    PAYMENT_VOID    = 'void'
    PAYMENT_REFUNDED = 'refunded'

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING,  'Pending'),
        (PAYMENT_PARTIAL,  'Partial'),
        (PAYMENT_PAID,     'Paid'),
        (PAYMENT_VOID,     'Void'),
        (PAYMENT_REFUNDED, 'Refunded'),
    ]

    order_number = models.CharField(
        max_length=30, unique=True, editable=False,
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.PROTECT,
        related_name='orders',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='orders',
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='orders',
    )
    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.PROTECT,
        related_name='orders',
        null=True, blank=True,
    )
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        related_name='orders',
        null=True, blank=True,
    )

    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    tax_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT,
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_PENDING,
    )

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_orders',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'{self.order_number} — {self.customer.name}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            with connection.cursor() as cursor:
                cursor.execute("SELECT nextval('order_number_seq')")
                num = cursor.fetchone()[0]
            self.order_number = f'ORD-{num:06d}'
        super().save(*args, **kwargs)