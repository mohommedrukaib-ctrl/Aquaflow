"""
AquaFlow — Wash Models
Powered by Quantum Axis

Includes:
- WashBay — physical wash bays
- WashJob — work orders (from booking or walk-in)
- WashJobItem — services, repairs, products per job
- RepairPart — parts used in repairs (linked to inventory)
- JobNote — printed slip for customer to collect car
"""

from django.db import models, connection
from django.contrib.auth.models import User
from decimal import Decimal


class WashBay(models.Model):

    STATUS_AVAILABLE   = 'available'
    STATUS_OCCUPIED    = 'occupied'
    STATUS_MAINTENANCE = 'maintenance'

    STATUS_CHOICES = [
        (STATUS_AVAILABLE,   'Available'),
        (STATUS_OCCUPIED,    'Occupied'),
        (STATUS_MAINTENANCE, 'Maintenance'),
    ]

    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='wash_bays',
    )
    name       = models.CharField(max_length=100)
    code       = models.CharField(max_length=20)
    status     = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_AVAILABLE,
    )
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = 'wash_bays'
        unique_together = ('branch', 'code')
        ordering        = ['branch', 'name']

    def __str__(self):
        return f'{self.name} ({self.branch.name})'


class WashJob(models.Model):

    STATUS_WAITING       = 'waiting'
    STATUS_ASSIGNED      = 'assigned'
    STATUS_WASHING       = 'washing'
    STATUS_QUALITY_CHECK = 'quality_check'
    STATUS_READY         = 'ready'
    STATUS_COMPLETED     = 'completed'
    STATUS_CANCELLED     = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_WAITING,       'Waiting'),
        (STATUS_ASSIGNED,      'Assigned'),
        (STATUS_WASHING,       'Washing'),
        (STATUS_QUALITY_CHECK, 'Quality Check'),
        (STATUS_READY,         'Ready'),
        (STATUS_COMPLETED,     'Completed'),
        (STATUS_CANCELLED,     'Cancelled'),
    ]

    PRIORITY_NORMAL = 'normal'
    PRIORITY_HIGH   = 'high'
    PRIORITY_URGENT = 'urgent'

    PRIORITY_CHOICES = [
        (PRIORITY_NORMAL, 'Normal'),
        (PRIORITY_HIGH,   'High'),
        (PRIORITY_URGENT, 'Urgent'),
    ]

    job_number = models.CharField(
        max_length=30, unique=True, editable=False,
    )

    # ─── Source ─────────────────────────────────────────────
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='wash_jobs',
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='wash_jobs',
    )
    invoice = models.ForeignKey(
        'invoices.Invoice',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='wash_jobs',
    )

    # ─── Details ────────────────────────────────────────────
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='wash_jobs',
    )
    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.PROTECT,
        related_name='wash_jobs',
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        related_name='wash_jobs',
        null=True, blank=True,
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='wash_jobs',
    )
    wash_bay = models.ForeignKey(
        WashBay,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='wash_jobs',
    )
    assigned_employee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_wash_jobs',
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_WAITING,
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_NORMAL,
    )

    notes         = models.TextField(blank=True)
    quality_notes = models.TextField(blank=True)

    # ─── Timing ─────────────────────────────────────────────
    scheduled_time      = models.DateTimeField(null=True, blank=True)
    estimated_completion = models.DateTimeField(
        null=True, blank=True,
        help_text='Estimated time car will be ready.',
    )
    started_at       = models.DateTimeField(null=True, blank=True)
    completed_at     = models.DateTimeField(null=True, blank=True)
    quality_check_at = models.DateTimeField(null=True, blank=True)

    # ─── Photos ─────────────────────────────────────────────
    photo_before = models.ImageField(
        upload_to='wash_photos/before/',
        null=True, blank=True,
    )
    photo_after = models.ImageField(
        upload_to='wash_photos/after/',
        null=True, blank=True,
    )

    # ─── Checklist ──────────────────────────────────────────
    checklist_exterior  = models.BooleanField(default=False)
    checklist_interior  = models.BooleanField(default=False)
    checklist_wheels    = models.BooleanField(default=False)
    checklist_windows   = models.BooleanField(default=False)
    checklist_dashboard = models.BooleanField(default=False)
    checklist_vacuum    = models.BooleanField(default=False)

    # ─── Warranty ───────────────────────────────────────────
    warranty_expiry = models.DateField(null=True, blank=True)

    # ─── Timestamps ─────────────────────────────────────────
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_wash_jobs',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wash_jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['branch', 'status']),
            models.Index(fields=['assigned_employee']),
        ]

    def __str__(self):
        return f'{self.job_number} — {self.vehicle.registration_number}'

    def save(self, *args, **kwargs):
        if not self.job_number:
            with connection.cursor() as cursor:
                cursor.execute("SELECT nextval('job_number_seq')")
                num = cursor.fetchone()[0]
            self.job_number = f'WJ-{num:06d}'
        super().save(*args, **kwargs)

    @property
    def duration_minutes(self):
        """Calculate wash duration in minutes."""
        if not self.started_at:
            return None
        end = self.completed_at or self.quality_check_at
        if not end:
            from django.utils import timezone
            end = timezone.now()
        delta = end - self.started_at
        return int(delta.total_seconds() / 60)

    @property
    def is_active(self):
        return self.status in [
            self.STATUS_WAITING,
            self.STATUS_ASSIGNED,
            self.STATUS_WASHING,
            self.STATUS_QUALITY_CHECK,
        ]

    @property
    def items_total(self):
        """Calculate total of all items in this job."""
        total = self.items.aggregate(
            models.Sum('total')
        )['total__sum']
        return total or Decimal('0')

    @property
    def parts_total(self):
        """Calculate total cost of all parts used."""
        total = Decimal('0')
        for item in self.items.filter(item_type='repair'):
            parts_sum = item.parts.aggregate(
                models.Sum('total_cost')
            )['total_cost__sum']
            total += parts_sum or Decimal('0')
        return total

    @property
    def grand_total(self):
        """Items total + parts total."""
        return self.items_total + self.parts_total

    @property
    def has_repairs(self):
        return self.items.filter(item_type='repair').exists()

    @property
    def has_services(self):
        return self.items.filter(item_type='service').exists()

    @property
    def has_products(self):
        return self.items.filter(item_type='product').exists()

    @property
    def item_count(self):
        return self.items.count()


class WashJobItem(models.Model):
    """
    Items in a wash job.
    Can be: Service, Repair, Product, Custom.
    Multiple items per job supported.
    Each item can have its own VAT setting.
    """

    TYPE_SERVICE = 'service'
    TYPE_REPAIR  = 'repair'
    TYPE_PRODUCT = 'product'
    TYPE_CUSTOM  = 'custom'

    TYPE_CHOICES = [
        (TYPE_SERVICE, 'Service'),
        (TYPE_REPAIR,  'Repair'),
        (TYPE_PRODUCT, 'Product'),
        (TYPE_CUSTOM,  'Custom'),
    ]

    STATUS_PENDING     = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED   = 'completed'
    STATUS_CANCELLED   = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING,     'Pending'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED,   'Completed'),
        (STATUS_CANCELLED,   'Cancelled'),
    ]

    wash_job = models.ForeignKey(
        WashJob,
        on_delete=models.CASCADE,
        related_name='items',
    )
    item_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_SERVICE,
    )

    # Item details (editable by cashier)
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    quantity    = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
    )
    unit_price  = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    total       = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )

    # VAT per item
    vat_applicable = models.BooleanField(default=True)

    # Status tracking (for repairs that take time)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    # Linked catalog items (optional)
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )

    # ─── Repair-specific fields ─────────────────────────────
    estimated_hours = models.DecimalField(
        max_digits=5, decimal_places=1, default=0,
        help_text='Estimated repair time in hours.',
    )
    warranty_days = models.PositiveIntegerField(
        default=0,
        help_text='Warranty period in days. 0 = no warranty.',
    )
    technician_notes = models.TextField(
        blank=True,
        help_text='Internal notes for technician.',
    )

    # Assigned employee for this specific item
    assigned_employee = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_job_items',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wash_job_items'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.name} x{self.quantity}'

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    @property
    def parts_cost(self):
        """Total cost of parts used for this item."""
        total = self.parts.aggregate(
            models.Sum('total_cost')
        )['total_cost__sum']
        return total or Decimal('0')

    @property
    def total_with_parts(self):
        """Item total + parts cost."""
        return self.total + self.parts_cost


class RepairPart(models.Model):
    """
    Parts used in a repair.
    Linked to inventory for stock tracking.
    When a part is added, inventory is deducted.
    """

    job_item = models.ForeignKey(
        WashJobItem,
        on_delete=models.CASCADE,
        related_name='parts',
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='repair_parts_used',
        null=True, blank=True,
    )
    name      = models.CharField(max_length=255)
    quantity  = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
    )
    unit_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    total_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    notes     = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'repair_parts'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.name} x{self.quantity}'

    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)


class JobNote(models.Model):
    """
    Printed slip given to customer when they drop off their car.
    Customer presents this note to collect their vehicle.

    Available in two formats:
    - Thermal receipt (80mm)
    - Half A4 black & white
    """

    wash_job = models.OneToOneField(
        WashJob,
        on_delete=models.CASCADE,
        related_name='job_note',
    )
    note_number = models.CharField(max_length=30, unique=True)

    # Snapshot fields (frozen at print time)
    customer_name  = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=50, blank=True)
    vehicle_reg    = models.CharField(max_length=50)
    vehicle_desc   = models.CharField(max_length=255, blank=True)

    items_summary = models.TextField(
        blank=True,
        help_text='List of services/repairs being done.',
    )
    estimated_time = models.CharField(
        max_length=100, blank=True,
        help_text='e.g., "2-3 hours", "Ready by 4 PM"',
    )
    special_instructions = models.TextField(
        blank=True,
        help_text='Customer special requests.',
    )

    # Tracking
    received_at  = models.DateTimeField(auto_now_add=True)
    printed_at   = models.DateTimeField(null=True, blank=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    collected_by = models.CharField(
        max_length=255, blank=True,
        help_text='Name of person who collected the vehicle.',
    )

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
    )

    class Meta:
        db_table = 'job_notes'
        ordering = ['-received_at']

    def __str__(self):
        return f'{self.note_number} — {self.vehicle_reg}'

    def save(self, *args, **kwargs):
        if not self.note_number:
            with connection.cursor() as cursor:
                # Try dedicated sequence first, fall back to job_number_seq
                try:
                    cursor.execute("SELECT nextval('job_note_seq')")
                except Exception:
                    cursor.execute("SELECT nextval('job_number_seq')")
                num = cursor.fetchone()[0]
            self.note_number = f'JN-{num:06d}'
        super().save(*args, **kwargs)

    @property
    def is_collected(self):
        return self.collected_at is not None

    @classmethod
    def create_from_wash_job(cls, wash_job, user=None):
        """
        Create a job note from a wash job.
        Snapshots current state.
        """
        # Build items summary
        items_lines = []
        for item in wash_job.items.all():
            type_label = item.get_item_type_display()
            items_lines.append(
                f'• {item.name} ({type_label}) x{item.quantity}'
            )

        items_summary = '\n'.join(items_lines) if items_lines else 'No items listed.'

        # Vehicle description
        vehicle = wash_job.vehicle
        vehicle_desc = f'{vehicle.brand.name} {vehicle.model.name}'
        if vehicle.color:
            vehicle_desc += f' ({vehicle.color.name})'
        if vehicle.year:
            vehicle_desc += f' [{vehicle.year}]'

        note = cls(
            wash_job=wash_job,
            customer_name=wash_job.customer.name,
            customer_phone=wash_job.customer.phone or '',
            vehicle_reg=vehicle.registration_number,
            vehicle_desc=vehicle_desc,
            items_summary=items_summary,
            estimated_time='',
            created_by=user,
        )
        note.save()
        return note