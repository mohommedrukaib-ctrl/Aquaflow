"""
AquaFlow — Inventory Models
Powered by Quantum Axis
"""

from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class ProductCategory(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    sort_order  = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'product_categories'
        ordering            = ['sort_order', 'name']
        verbose_name        = 'Product Category'
        verbose_name_plural = 'Product Categories'

    def __str__(self):
        return self.name


class Unit(models.Model):
    name         = models.CharField(max_length=50, unique=True)
    abbreviation = models.CharField(max_length=20, unique=True)
    is_active    = models.BooleanField(default=True)

    class Meta:
        db_table = 'units'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.abbreviation})'


class Product(models.Model):
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        related_name='products',
        null=True, blank=True,
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name='products',
        null=True, blank=True,
    )
    sku = models.CharField(
        max_length=50, unique=True, blank=True,
        help_text='Auto-generated if blank.',
    )
    barcode = models.CharField(
        max_length=100, blank=True,
        help_text='Product barcode (optional).',
    )
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)

    cost_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    reorder_level = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Alert when stock falls to this level.',
    )
    reorder_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Suggested reorder amount.',
    )

    is_active  = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='deleted_products',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_products',
    )

    class Meta:
        db_table            = 'products'
        ordering            = ['name']
        verbose_name        = 'Product'
        verbose_name_plural = 'Products'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['sku']),
            models.Index(fields=['is_deleted']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.sku:
            import uuid
            self.sku = f'P-{str(uuid.uuid4().int)[:8]}'
        super().save(*args, **kwargs)

    def get_stock(self, branch=None):
        """Get total stock across branches (or specific branch)."""
        qs = self.stock_entries.all()
        if branch:
            qs = qs.filter(branch=branch)
        total = qs.aggregate(models.Sum('quantity'))['quantity__sum']
        return total or Decimal('0')

    @property
    def is_low_stock(self):
        """Check if stock is below reorder level."""
        if self.reorder_level <= 0:
            return False
        return self.get_stock() <= self.reorder_level


class InventoryStock(models.Model):
    """Current stock level per product per branch."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_entries',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        related_name='inventory_stock',
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'inventory_stock'
        unique_together     = ('product', 'branch')
        verbose_name        = 'Inventory Stock'
        verbose_name_plural = 'Inventory Stock'

    def __str__(self):
        return f'{self.product.name} @ {self.branch.name}: {self.quantity}'


class InventoryTransaction(models.Model):
    """
    Every stock movement is recorded here.
    NEVER delete these — this is the audit trail.
    """

    TYPE_PURCHASE   = 'purchase'
    TYPE_SALE       = 'sale'
    TYPE_ADJUSTMENT = 'adjustment'
    TYPE_TRANSFER   = 'transfer'
    TYPE_RETURN     = 'return'
    TYPE_USAGE      = 'usage'      # Used during wash service
    TYPE_INITIAL    = 'initial'    # Opening stock

    TYPE_CHOICES = [
        (TYPE_PURCHASE,   'Purchase'),
        (TYPE_SALE,       'Sale'),
        (TYPE_ADJUSTMENT, 'Adjustment'),
        (TYPE_TRANSFER,   'Transfer'),
        (TYPE_RETURN,     'Return'),
        (TYPE_USAGE,      'Usage'),
        (TYPE_INITIAL,    'Initial Stock'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='transactions',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='inventory_transactions',
    )
    transaction_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, db_index=True,
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text='Positive for IN, negative for OUT.',
    )
    quantity_before = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    quantity_after = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    unit_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Cost per unit at time of transaction.',
    )

    # Optional linked records
    reference_id   = models.CharField(max_length=100, blank=True)
    reference_type = models.CharField(max_length=50, blank=True)

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='inventory_transactions',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table            = 'inventory_transactions'
        ordering            = ['-created_at']
        verbose_name        = 'Inventory Transaction'
        verbose_name_plural = 'Inventory Transactions'
        indexes = [
            models.Index(fields=['product', '-created_at']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['branch', '-created_at']),
        ]

    def __str__(self):
        sign = '+' if self.quantity > 0 else ''
        return f'{self.product.name}: {sign}{self.quantity} ({self.get_transaction_type_display()})'