"""
AquaFlow — Employee Models
Powered by Quantum Axis
"""

from django.db import models, connection
from django.contrib.auth.models import User


class EmployeePosition(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'employee_positions'
        ordering = ['name']

    def __str__(self):
        return self.name


class Employee(models.Model):

    STATUS_ACTIVE   = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_ON_LEAVE = 'on_leave'

    STATUS_CHOICES = [
        (STATUS_ACTIVE,   'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_ON_LEAVE, 'On Leave'),
    ]

    employee_code = models.CharField(
        max_length=20, unique=True, editable=False,
    )

    # Link to Django user (optional — for employees who log in)
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='employee_record',
    )

    # Personal info
    first_name = models.CharField(max_length=100)
    last_name  = models.CharField(max_length=100, blank=True)
    phone      = models.CharField(max_length=50, blank=True, db_index=True)
    phone2     = models.CharField(max_length=50, blank=True)
    email      = models.EmailField(blank=True)
    address    = models.TextField(blank=True)
    nic_number = models.CharField(
        max_length=50, blank=True,
        help_text='National ID / Passport number.',
    )

    # Employment
    position = models.ForeignKey(
        EmployeePosition,
        on_delete=models.PROTECT,
        related_name='employees',
        null=True, blank=True,
    )
    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='employees',
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.PROTECT,
        related_name='employees',
    )

    hire_date = models.DateField(null=True, blank=True)
    salary    = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
    )
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Commission % on sales.',
    )

    # Photo
    photo = models.ImageField(
        upload_to='employees/photos/',
        null=True, blank=True,
    )

    notes = models.TextField(blank=True)

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_ACTIVE, db_index=True,
    )

    # Soft delete
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='deleted_employees',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_employees',
    )

    class Meta:
        db_table = 'employees'
        ordering = ['first_name', 'last_name']
        indexes = [
            models.Index(fields=['is_deleted']),
            models.Index(fields=['status']),
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return f'{self.full_name} ({self.employee_code})'

    @property
    def full_name(self):
        if self.last_name:
            return f'{self.first_name} {self.last_name}'
        return self.first_name

    def save(self, *args, **kwargs):
        if not self.employee_code:
            with connection.cursor() as cursor:
                cursor.execute("SELECT nextval('employee_code_seq')")
                seq = cursor.fetchone()[0]
            self.employee_code = f'EMP-{seq:04d}'
        if not self.business_id:
            from apps.businesses.models import Business
            self.business = Business.objects.get(pk=1)
        super().save(*args, **kwargs)

    def soft_delete(self, user=None):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])