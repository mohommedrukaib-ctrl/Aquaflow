"""
AquaFlow — Payment Models
Powered by Quantum Axis
"""

from django.db import models
from django.contrib.auth.models import User


class PaymentMethod(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    code       = models.CharField(max_length=50,  unique=True)
    is_active  = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_methods'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Payment(models.Model):

    STATUS_PENDING   = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED    = 'failed'
    STATUS_REFUNDED  = 'refunded'

    STATUS_CHOICES = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED,    'Failed'),
        (STATUS_REFUNDED,  'Refunded'),
    ]

    invoice = models.ForeignKey(
        'invoices.Invoice',
        on_delete=models.PROTECT,
        related_name='payments',
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='payments',
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='payments',
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
    )
    reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_COMPLETED,
    )
    notes = models.TextField(blank=True)

    processed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
    )
    processed_at = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-processed_at']

    def __str__(self):
        return f'{self.invoice.invoice_number} — {self.amount}'