"""
AquaFlow — Supplier & Purchase Models
Powered by Quantum Axis
"""

from django.db import models, connection
from django.contrib.auth.models import User
from decimal import Decimal


class Supplier(models.Model):
    name           = models.CharField(max_length=255, db_index=True)
    contact_person = models.CharField(max_length=255, blank=True)
    phone          = models.CharField(max_length=50, blank=True, db_index=True)
    phone2         = models.CharField(max_length=50, blank=True)
    email          = models.EmailField(blank=True)
    address        = models.TextField(blank=True)
    tax_number     = models.CharField(max_length=100, blank=True)
    notes          = models.TextField(blank=True)

    is_active  = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='deleted_suppliers',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_suppliers',
    )

    class Meta:
        db_table   = 'suppliers'
        ordering   = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return self.name

    @property
    def total_purchases(self):
        return self.purchases.aggregate(
            models.Sum('total')
        )['total__sum'] or Decimal('0')

    @property
    def outstanding_balance(self):
        """Money owed to this supplier."""
        purchases = self.purchases.aggregate(
            models.Sum('total')
        )['total__sum'] or Decimal('0')
        paid = self.purchases.aggregate(
            models.Sum('amount_paid')
        )['amount_paid__sum'] or Decimal('0')
        return purchases - paid


class Purchase(models.Model):

    STATUS_DRAFT     = 'draft'
    STATUS_RECEIVED  = 'received'
    STATUS_PARTIAL   = 'partial'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_DRAFT,     'Draft'),
        (STATUS_RECEIVED,  'Received'),
        (STATUS_PARTIAL,   'Partial'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    PAYMENT_UNPAID  = 'unpaid'
    PAYMENT_PARTIAL = 'partial'
    PAYMENT_PAID    = 'paid'

    PAYMENT_CHOICES = [
        (PAYMENT_UNPAID,  'Unpaid'),
        (PAYMENT_PARTIAL, 'Partial'),
        (PAYMENT_PAID,    'Paid'),
    ]

    purchase_number = models.CharField(
        max_length=30, unique=True, editable=False,
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchases',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='purchases',
    )

    purchase_date = models.DateField(db_index=True)
    invoice_ref   = models.CharField(
        max_length=100, blank=True,
        help_text='Supplier invoice reference number.',
    )

    subtotal        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total           = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid     = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    status         = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT,
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_UNPAID,
    )

    notes      = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_purchases',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'purchases'
        ordering = ['-purchase_date', '-created_at']

    def __str__(self):
        return f'{self.purchase_number} — {self.supplier.name}'

    def save(self, *args, **kwargs):
        if not self.purchase_number:
            with connection.cursor() as cursor:
                cursor.execute("SELECT nextval('purchase_number_seq')")
                num = cursor.fetchone()[0]
            self.purchase_number = f'PUR-{num:06d}'
        super().save(*args, **kwargs)

    @property
    def outstanding(self):
        return self.total - self.amount_paid


class PurchaseItem(models.Model):
    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='purchase_items',
    )
    quantity   = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost  = models.DecimalField(max_digits=12, decimal_places=2)
    total      = models.DecimalField(max_digits=12, decimal_places=2)
    notes      = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'purchase_items'
        ordering = ['id']

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'