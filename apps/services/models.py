"""
AquaFlow — Services Models
Powered by Quantum Axis

Service categories, services and pricing.
Prices can vary by vehicle type and branch.
Price snapshots are stored in invoice_items
so old invoices never change when prices change.
"""

from django.db import models
from django.contrib.auth.models import User


# ─── Service Category ─────────────────────────────────────────

class ServiceCategory(models.Model):

    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    sort_order  = models.PositiveIntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'service_categories'
        ordering            = ['sort_order', 'name']
        verbose_name        = 'Service Category'
        verbose_name_plural = 'Service Categories'

    def __str__(self):
        return self.name


# ─── Service ──────────────────────────────────────────────────

class Service(models.Model):

    # ─── Identity ─────────────────────────────────────────────
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name='services',
        null=True,
        blank=True,
    )
    name        = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(
        default=30,
        help_text='Estimated duration in minutes.',
    )

    # ─── Tax Override ─────────────────────────────────────────
    # If None → uses business default tax setting
    tax_override_enabled    = models.BooleanField(
        default=False,
        help_text='Override business tax setting for this service.',
    )
    tax_override_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Custom tax % for this service.',
    )

    # ─── Status ───────────────────────────────────────────────
    is_active  = models.BooleanField(default=True)

    # ─── Soft Delete ──────────────────────────────────────────
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_services',
    )

    # ─── Timestamps ───────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_services',
    )

    class Meta:
        db_table            = 'services'
        ordering            = ['category__sort_order', 'name']
        verbose_name        = 'Service'
        verbose_name_plural = 'Services'
        indexes = [
            models.Index(fields=['is_deleted']),
            models.Index(fields=['is_active']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name

    def soft_delete(self, user=None):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=[
            'is_deleted', 'deleted_at', 'deleted_by'
        ])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=[
            'is_deleted', 'deleted_at', 'deleted_by'
        ])

    def get_price(self, vehicle_type=None, branch=None):
        """
        Returns the best matching price for this service.

        Priority:
          1. Branch + vehicle type specific
          2. Branch specific (any vehicle type)
          3. Vehicle type specific (any branch)
          4. Default price (no branch, no vehicle type)
          5. None if no price configured
        """
        from django.utils import timezone
        now = timezone.now().date()

        prices = self.prices.filter(
            is_active=True,
        ).filter(
            models.Q(effective_from__lte=now) | models.Q(effective_from__isnull=True)
        ).filter(
            models.Q(effective_to__gte=now) | models.Q(effective_to__isnull=True)
        )

        # 1. Branch + Vehicle Type
        if branch and vehicle_type:
            p = prices.filter(
                branch=branch,
                vehicle_type=vehicle_type
            ).first()
            if p:
                return p

        # 2. Branch only
        if branch:
            p = prices.filter(
                branch=branch,
                vehicle_type__isnull=True
            ).first()
            if p:
                return p

        # 3. Vehicle type only
        if vehicle_type:
            p = prices.filter(
                branch__isnull=True,
                vehicle_type=vehicle_type
            ).first()
            if p:
                return p

        # 4. Default
        p = prices.filter(
            branch__isnull=True,
            vehicle_type__isnull=True
        ).first()
        return p

    def get_price_amount(self, vehicle_type=None, branch=None):
        """Returns Decimal price or 0 (never None)."""
        from decimal import Decimal
        price = self.get_price(vehicle_type=vehicle_type, branch=branch)
        return price.price if price else Decimal('0.00')

    @property
    def duration_display(self):
        if self.duration_minutes < 60:
            return f'{self.duration_minutes} min'
        hours   = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        if minutes:
            return f'{hours}h {minutes}min'
        return f'{hours}h'


# ─── Service Price ────────────────────────────────────────────

class ServicePrice(models.Model):
    """
    Flexible pricing:
    - Default price (no vehicle type, no branch)
    - Vehicle-type specific price
    - Branch specific price
    - Branch + vehicle type specific price
    - Date-range based pricing (promotions)

    When a sale is made, price is SNAPSHOTTED into invoice_items.
    Changing price here NEVER affects old invoices.
    """

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='prices',
    )
    vehicle_type = models.ForeignKey(
        'vehicles.VehicleType',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='service_prices',
        help_text='Leave blank for all vehicle types.',
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='service_prices',
        help_text='Leave blank for all branches.',
    )

    # ─── Price ────────────────────────────────────────────────
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Price in LKR (or configured currency).',
    )

    # ─── Date Range (for promotions) ──────────────────────────
    effective_from = models.DateField(
        null=True,
        blank=True,
        help_text='Leave blank to apply immediately.',
    )
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text='Leave blank for no expiry.',
    )

    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table   = 'service_prices'
        ordering   = ['service', 'vehicle_type', 'branch']
        verbose_name        = 'Service Price'
        verbose_name_plural = 'Service Prices'
        constraints = [
            models.UniqueConstraint(
                fields=['service', 'vehicle_type', 'branch'],
                name='unique_service_price',
            )
        ]

    def __str__(self):
        parts = [self.service.name]
        if self.vehicle_type:
            parts.append(self.vehicle_type.name)
        if self.branch:
            parts.append(self.branch.name)
        return ' / '.join(parts) + f' → Rs. {self.price}'