"""
AquaFlow — Service Forms
Powered by Quantum Axis
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Service, ServiceCategory, ServicePrice


class ServiceCategoryForm(forms.ModelForm):

    class Meta:
        model  = ServiceCategory
        fields = ['name', 'description', 'sort_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Category name',
                'autofocus':   True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows':  2,
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min':   0,
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        existing = ServiceCategory.objects.filter(
            name__iexact=name
        ).exclude(
            pk=self.instance.pk if self.instance.pk else None
        )
        if existing.exists():
            raise ValidationError(
                f'Category "{name}" already exists.'
            )
        return name


class ServiceForm(forms.ModelForm):

    class Meta:
        model  = Service
        fields = [
            'category',
            'name',
            'description',
            'duration_minutes',
            'tax_override_enabled',
            'tax_override_percentage',
            'is_active',
        ]
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'name': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Service name',
                'autofocus':   True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows':  3,
                'placeholder': 'Describe this service...',
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min':   5,
                'max':   480,
            }),
            'tax_override_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id':    'id_tax_override_enabled',
            }),
            'tax_override_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min':   0,
                'max':   100,
                'step':  '0.01',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ServiceCategory.objects.filter(
            is_active=True
        ).order_by('sort_order', 'name')
        self.fields['category'].empty_label = '— No Category —'

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('Service name is required.')
        return name

    def clean_tax_override_percentage(self):
        pct = self.cleaned_data.get('tax_override_percentage', 0)
        if pct and (pct < 0 or pct > 100):
            raise ValidationError(
                'Tax percentage must be between 0 and 100.'
            )
        return pct


class ServicePriceForm(forms.ModelForm):

    class Meta:
        model  = ServicePrice
        fields = [
            'vehicle_type',
            'branch',
            'price',
            'effective_from',
            'effective_to',
            'is_active',
        ]
        widgets = {
            'vehicle_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'branch': forms.Select(attrs={
                'class': 'form-select',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min':   0,
                'step':  '0.01',
                'placeholder': '0.00',
            }),
            'effective_from': forms.DateInput(attrs={
                'class': 'form-control',
                'type':  'date',
            }),
            'effective_to': forms.DateInput(attrs={
                'class': 'form-control',
                'type':  'date',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.service = kwargs.pop('service', None)
        super().__init__(*args, **kwargs)

        from apps.vehicles.models import VehicleType
        from apps.branches.models import Branch

        self.fields['vehicle_type'].queryset = VehicleType.objects.filter(
            is_active=True
        ).order_by('sort_order', 'name')
        self.fields['vehicle_type'].empty_label = '— All Vehicle Types —'

        self.fields['branch'].queryset = Branch.objects.filter(
            status='active'
        ).order_by('name')
        self.fields['branch'].empty_label = '— All Branches —'

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is None or price < 0:
            raise ValidationError('Price must be 0 or greater.')
        return price

    def clean(self):
        cleaned_data  = super().clean()
        vehicle_type  = cleaned_data.get('vehicle_type')
        branch        = cleaned_data.get('branch')
        effective_from = cleaned_data.get('effective_from')
        effective_to   = cleaned_data.get('effective_to')

        if effective_from and effective_to:
            if effective_to < effective_from:
                raise ValidationError(
                    'Effective To date must be after Effective From.'
                )

        # Check duplicate price entry
        if self.service:
            existing = ServicePrice.objects.filter(
                service=self.service,
                vehicle_type=vehicle_type,
                branch=branch,
            ).exclude(
                pk=self.instance.pk if self.instance.pk else None
            )
            if existing.exists():
                vt_name = vehicle_type.name if vehicle_type else 'All types'
                br_name = branch.name if branch else 'All branches'
                raise ValidationError(
                    f'A price for {vt_name} / {br_name} '
                    f'already exists for this service. '
                    f'Edit the existing price instead.'
                )

        return cleaned_data