"""
AquaFlow — Booking Forms
Powered by Quantum Axis
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import Booking
from apps.customers.models import Customer
from apps.vehicles.models import Vehicle
from apps.services.models import Service
from apps.branches.models import Branch
from apps.wash.models import WashBay


class BookingForm(forms.ModelForm):

    class Meta:
        model = Booking
        fields = [
            'customer',
            'vehicle',
            'service',
            'branch',
            'scheduled_date',
            'scheduled_time',
            'assigned_employee',
            'wash_bay',
            'status',
            'notes',
        ]
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_customer',
            }),
            'vehicle': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_vehicle',
            }),
            'service': forms.Select(attrs={
                'class': 'form-select',
            }),
            'branch': forms.Select(attrs={
                'class': 'form-select',
            }),
            'scheduled_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'scheduled_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
            }),
            'assigned_employee': forms.Select(attrs={
                'class': 'form-select',
            }),
            'wash_bay': forms.Select(attrs={
                'class': 'form-select',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional booking notes',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ─── Status not required (defaults to PENDING) ─────────
        self.fields['status'].required = False

        self.fields['customer'].queryset = (
            Customer.objects
            .filter(is_deleted=False, status='active')
            .order_by('name')
        )

        self.fields['vehicle'].queryset = (
            Vehicle.objects
            .filter(is_deleted=False, status='active')
            .select_related('customer', 'brand', 'model')
            .order_by('registration_number')
        )

        self.fields['service'].queryset = (
            Service.objects
            .filter(is_deleted=False, is_active=True)
            .order_by('name')
        )

        self.fields['branch'].queryset = Branch.objects.filter(
            status='active'
        ).order_by('name')

        self.fields['wash_bay'].queryset = WashBay.objects.filter(
            is_active=True
        ).order_by('branch__name', 'name')

        self.fields['assigned_employee'].queryset = (
            self.fields['assigned_employee']
            .queryset
            .filter(is_active=True)
            .order_by('username')
        )
    
    def clean(self):
        cleaned_data = super().clean()

        customer = cleaned_data.get('customer')
        vehicle = cleaned_data.get('vehicle')
        service = cleaned_data.get('service')
        branch = cleaned_data.get('branch')
        date = cleaned_data.get('scheduled_date')
        time = cleaned_data.get('scheduled_time')

        # ─── Default status to PENDING ────────────────────────
        if not cleaned_data.get('status'):
            cleaned_data['status'] = Booking.STATUS_PENDING

        if customer and vehicle and vehicle.customer_id != customer.pk:
            raise ValidationError(
                'The selected vehicle does not belong to the selected customer.'
            )

        if service:
            cleaned_data['duration_minutes'] = service.duration_minutes

        if branch and date and time:
            conflict = Booking.objects.filter(
                branch=branch,
                scheduled_date=date,
                scheduled_time=time,
                status__in=[
                    Booking.STATUS_PENDING,
                    Booking.STATUS_CONFIRMED,
                    Booking.STATUS_ARRIVED,
                ],
            ).exclude(pk=self.instance.pk)

            if conflict.exists():
                raise ValidationError(
                    'This branch already has an active booking at that time.'
                )

        return cleaned_data