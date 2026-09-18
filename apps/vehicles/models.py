"""
AquaFlow — Vehicle Models
Powered by Quantum Axis

Brands, Models, Vehicle Types, Colors, Fuel Types, Vehicles.
Case-insensitive uniqueness on brands and models.
Registration number is unique and indexed.
Soft delete — never physically delete vehicles with history.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


# ─── Vehicle Type ─────────────────────────────────────────────

class VehicleType(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    sort_order  = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'vehicle_types'
        ordering            = ['sort_order', 'name']
        verbose_name        = 'Vehicle Type'
        verbose_name_plural = 'Vehicle Types'

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ─── Color ────────────────────────────────────────────────────

class Color(models.Model):
    name      = models.CharField(max_length=100, unique=True)
    hex_code  = models.CharField(
        max_length=7,
        blank=True,
        help_text='Hex color code. Example: #FF0000',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'colors'
        ordering = ['name']

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ─── Fuel Type ────────────────────────────────────────────────

class FuelType(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        db_table = 'fuel_types'
        ordering = ['name']

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ─── Brand ────────────────────────────────────────────────────

class Brand(models.Model):
    name       = models.CharField(max_length=100)
    slug       = models.SlugField(max_length=120, unique=True, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'brands'
        ordering = ['name']
        verbose_name        = 'Brand'
        verbose_name_plural = 'Brands'
        constraints = [
            models.UniqueConstraint(
                models.functions.Lower('name'),
                name='unique_brand_name_ci',
            )
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        if not self.slug:
            base_slug = slugify(self.name)
            slug      = base_slug
            counter   = 1
            while Brand.objects.filter(
                slug=slug
            ).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_safe(cls, name):
        """
        Case-insensitive get or create.
        All names stored as UPPERCASE.
        """
        name = name.strip().upper()
        existing = cls.objects.filter(name__iexact=name).first()
        if existing:
            return existing, False
        return cls.objects.create(name=name), True


# ─── Vehicle Model ────────────────────────────────────────────

class VehicleModel(models.Model):
    brand      = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='models',
    )
    name       = models.CharField(max_length=100)
    slug       = models.SlugField(max_length=120, blank=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_models'
        ordering = ['brand__name', 'name']
        verbose_name        = 'Vehicle Model'
        verbose_name_plural = 'Vehicle Models'
        constraints = [
            models.UniqueConstraint(
                'brand',
                models.functions.Lower('name'),
                name='unique_model_brand_name_ci',
            )
        ]

    def __str__(self):
        return f'{self.brand.name} {self.name}'

    def save(self, *args, **kwargs):
        self.name = self.name.strip().upper()
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_safe(cls, brand, name):
        """
        Case-insensitive get or create for a brand.
        All names stored as UPPERCASE.
        """
        name = name.strip().upper()
        existing = cls.objects.filter(
            brand=brand,
            name__iexact=name,
        ).first()
        if existing:
            return existing, False
        return cls.objects.create(brand=brand, name=name), True


# ─── Vehicle ──────────────────────────────────────────────────

class Vehicle(models.Model):

    STATUS_ACTIVE   = 'active'
    STATUS_INACTIVE = 'inactive'

    STATUS_CHOICES = [
        (STATUS_ACTIVE,   'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]

    # ─── Ownership ────────────────────────────────────────────
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='vehicles',
    )

    # ─── Classification ───────────────────────────────────────
    brand        = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name='vehicles',
    )
    model        = models.ForeignKey(
        VehicleModel,
        on_delete=models.PROTECT,
        related_name='vehicles',
    )
    vehicle_type = models.ForeignKey(
        VehicleType,
        on_delete=models.PROTECT,
        related_name='vehicles',
        null=True,
        blank=True,
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicles',
    )
    fuel_type = models.ForeignKey(
        FuelType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicles',
    )

    # ─── Identity ─────────────────────────────────────────────
    registration_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text='Vehicle registration plate. Must be unique.',
    )
    year    = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Manufacturing year.',
    )
    mileage = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Current mileage in km.',
    )
    notes   = models.TextField(blank=True)

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
        related_name='deleted_vehicles',
    )

    # ─── Timestamps ───────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_vehicles',
    )

    class Meta:
        db_table            = 'vehicles'
        verbose_name        = 'Vehicle'
        verbose_name_plural = 'Vehicles'
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['registration_number']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['status']),
            models.Index(fields=['customer']),
        ]

    def __str__(self):
        return (
            f'{self.registration_number} — '
            f'{self.brand.name} {self.model.name}'
        )

    def save(self, *args, **kwargs):
        # Auto-uppercase registration number
        if self.registration_number:
            self.registration_number = self.registration_number.strip().upper()
        super().save(*args, **kwargs)

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

    @property
    def display_name(self):
        return (
            f'{self.brand.name} {self.model.name}'
            + (f' ({self.year})' if self.year else '')
        )

    @property
    def reg_number_clean(self):
        """Uppercase registration number."""
        return self.registration_number.upper()