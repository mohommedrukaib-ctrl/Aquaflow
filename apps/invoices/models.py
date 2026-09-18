"""
AquaFlow — Invoice Models
Powered by Quantum Axis
"""

from django.db import models, connection
from decimal import Decimal


class Invoice(models.Model):

    STATUS_DRAFT     = 'draft'
    STATUS_ISSUED    = 'issued'
    STATUS_PAID      = 'paid'
    STATUS_PARTIAL   = 'partial'
    STATUS_VOID      = 'void'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_DRAFT,     'Draft'),
        (STATUS_ISSUED,    'Issued'),
        (STATUS_PAID,      'Paid'),
        (STATUS_PARTIAL,   'Partial'),
        (STATUS_VOID,      'Void'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.PROTECT,
        related_name='invoice',
    )
    invoice_number = models.CharField(
        max_length=30, unique=True, editable=False,
    )

    issue_date = models.DateField(auto_now_add=True)
    due_date   = models.DateField(null=True, blank=True)

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
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ISSUED,
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'invoices'
        ordering = ['-created_at']

    def __str__(self):
        return self.invoice_number

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            with connection.cursor() as cursor:
                cursor.execute("SELECT nextval('invoice_number_seq')")
                num = cursor.fetchone()[0]
            self.invoice_number = f'INV-{num:06d}'
        super().save(*args, **kwargs)


class InvoiceItem(models.Model):
    """
    IMPORTANT: All fields with _snapshot suffix are frozen at time of sale.
    Old invoices NEVER change even if service prices are updated later.
    """

    ITEM_TYPE_SERVICE = 'service'
    ITEM_TYPE_PRODUCT = 'product'

    ITEM_TYPE_CHOICES = [
        (ITEM_TYPE_SERVICE, 'Service'),
        (ITEM_TYPE_PRODUCT, 'Product'),
    ]

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='items',
    )
    item_type = models.CharField(
        max_length=20, choices=ITEM_TYPE_CHOICES,
    )

    service = models.ForeignKey(
        'services.Service',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoice_items',
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoice_items',
    )

    # ─── SNAPSHOTS (never change) ─────────────────────────────
    description_snapshot = models.CharField(max_length=255)
    unit_price_snapshot  = models.DecimalField(
        max_digits=12, decimal_places=2,
    )

    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
    )
    discount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    line_total = models.DecimalField(
        max_digits=12, decimal_places=2,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'invoice_items'
        ordering = ['id']

    def __str__(self):
        return f'{self.description_snapshot} x{self.quantity}'