"""
AquaFlow — Booking Model
Powered by Quantum Axis
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Booking(models.Model):

    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_ARRIVED = 'arrived'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_NO_SHOW = 'no_show'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_ARRIVED, 'Arrived'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_NO_SHOW, 'No Show'),
    ]

    booking_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )

    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.PROTECT,
        related_name='bookings',
    )

    branch = models.ForeignKey(
        'branches.Branch',
        on_delete=models.PROTECT,
        related_name='bookings',
    )

    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='bookings',
    )

    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.PROTECT,
        related_name='bookings',
    )

    service = models.ForeignKey(
        'services.Service',
        on_delete=models.PROTECT,
        related_name='bookings',
    )

    assigned_employee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_bookings',
    )

    wash_bay = models.ForeignKey(
        'wash.WashBay',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
    )

    scheduled_date = models.DateField(db_index=True)
    scheduled_time = models.TimeField(db_index=True)

    duration_minutes = models.PositiveIntegerField(default=30)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    notes = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_bookings',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings'
        ordering = ['scheduled_date', 'scheduled_time']
        indexes = [
            models.Index(fields=['scheduled_date', 'status']),
            models.Index(fields=['branch', 'scheduled_date']),
            models.Index(fields=['customer']),
            models.Index(fields=['vehicle']),
        ]

    def __str__(self):
        return f'{self.booking_number} — {self.customer.name}'

    def save(self, *args, **kwargs):
        if not self.booking_number:
            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT nextval('booking_number_seq')"
                )
                number = cursor.fetchone()[0]

            self.booking_number = f'BK-{number:05d}'

        if self.service_id and not self.duration_minutes:
            self.duration_minutes = self.service.duration_minutes

        super().save(*args, **kwargs)

    def clean(self):
        if self.vehicle_id and self.customer_id:
            if self.vehicle.customer_id != self.customer_id:
                raise ValidationError(
                    'The selected vehicle does not belong to this customer.'
                )

        if self.service_id and self.duration_minutes <= 0:
            self.duration_minutes = self.service.duration_minutes

        if self.status in [
            self.STATUS_CANCELLED,
            self.STATUS_COMPLETED,
            self.STATUS_NO_SHOW,
        ]:
            return

        conflict = Booking.objects.filter(
            branch=self.branch,
            scheduled_date=self.scheduled_date,
            scheduled_time=self.scheduled_time,
            status__in=[
                self.STATUS_PENDING,
                self.STATUS_CONFIRMED,
                self.STATUS_ARRIVED,
            ],
        ).exclude(pk=self.pk)

        if conflict.exists():
            raise ValidationError(
                'Another active booking already exists at this date and time.'
            )