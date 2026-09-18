"""
AquaFlow — Vehicle Forms
Powered by Quantum Axis
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Vehicle, Brand, VehicleModel, VehicleType, Color, FuelType


class BrandForm(forms.ModelForm):

    class Meta:
        model  = Brand
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Brand name (e.g. Toyota)',
                'autofocus':   True,
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('Brand name is required.')

        # Case-insensitive uniqueness check
        existing = Brand.objects.filter(
            name__iexact=name
        ).exclude(pk=self.instance.pk if self.instance.pk else None)

        if existing.exists():
            raise ValidationError(
                f'Brand "{name}" already exists. '
                f'Check: {existing.first().name}'
            )
        return name


class VehicleModelForm(forms.ModelForm):

    class Meta:
        model  = VehicleModel
        fields = ['brand', 'name', 'is_active']
        widgets = {
            'brand': forms.Select(attrs={
                'class': 'form-select',
                'id':    'id_brand',
            }),
            'name': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Model name (e.g. Corolla)',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        brand = cleaned_data.get('brand')
        name  = cleaned_data.get('name', '').strip()

        if brand and name:
            existing = VehicleModel.objects.filter(
                brand=brand,
                name__iexact=name,
            ).exclude(
                pk=self.instance.pk if self.instance.pk else None
            )
            if existing.exists():
                raise ValidationError(
                    f'Model "{name}" already exists '
                    f'under {brand.name}.'
                )
        return cleaned_data


class VehicleForm(forms.ModelForm):

    # Brand selector (for dynamic model loading)
    brand_id = forms.IntegerField(
        widget=forms.HiddenInput(),
        required=False,
    )

    class Meta:
        model  = Vehicle
        fields = [
            'customer',
            'brand',
            'model',
            'vehicle_type',
            'color',
            'fuel_type',
            'registration_number',
            'year',
            'mileage',
            'notes',
            'status',
        ]
        widgets = {
            'customer': forms.Select(attrs={
                'class': 'form-select',
            }),
            'brand': forms.Select(attrs={
                'class': 'form-select',
                'id':    'id_brand',
            }),
            'model': forms.Select(attrs={
                'class': 'form-select',
                'id':    'id_model',
            }),
            'vehicle_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'color': forms.Select(attrs={
                'class': 'form-select',
            }),
            'fuel_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'registration_number': forms.TextInput(attrs={
                'class':       'form-control text-uppercase',
                'placeholder': 'e.g. WP CAA-1234',
                'autofocus':   True,
            }),
            'year': forms.NumberInput(attrs={
                'class':       'form-control',
                'placeholder': 'e.g. 2020',
                'min':         1950,
                'max':         2099,
            }),
            'mileage': forms.NumberInput(attrs={
                'class':       'form-control',
                'placeholder': 'Current mileage in km',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows':  2,
                'placeholder': 'Notes (optional)',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.customer_id = kwargs.pop('customer_id', None)
        super().__init__(*args, **kwargs)

        # Pre-select customer if provided
        if self.customer_id:
            self.fields['customer'].initial = self.customer_id
            self.fields['customer'].widget = forms.HiddenInput()

        # Only active brands
        self.fields['brand'].queryset = Brand.objects.filter(
            is_active=True
        ).order_by('name')

        # Only active vehicle types
        self.fields['vehicle_type'].queryset = VehicleType.objects.filter(
            is_active=True
        ).order_by('sort_order', 'name')

        # Only active colors
        self.fields['color'].queryset = Color.objects.filter(
            is_active=True
        ).order_by('name')

        # Only active fuel types
        self.fields['fuel_type'].queryset = FuelType.objects.filter(
            is_active=True
        ).order_by('name')

        # Models filtered by brand if editing
        if self.instance.pk and self.instance.brand_id:
            self.fields['model'].queryset = VehicleModel.objects.filter(
                brand=self.instance.brand,
                is_active=True,
            ).order_by('name')
        elif self.data.get('brand'):
            try:
                brand_id = int(self.data['brand'])
                self.fields['model'].queryset = VehicleModel.objects.filter(
                    brand_id=brand_id,
                    is_active=True,
                ).order_by('name')
            except (ValueError, TypeError):
                self.fields['model'].queryset = VehicleModel.objects.none()
        else:
            self.fields['model'].queryset = VehicleModel.objects.none()

    def clean_registration_number(self):
        reg = self.cleaned_data.get(
            'registration_number', ''
        ).strip().upper()

        if not reg:
            raise ValidationError('Registration number is required.')

        # Check uniqueness (excluding self on edit)
        existing = Vehicle.objects.filter(
            registration_number__iexact=reg,
            is_deleted=False,
        ).exclude(pk=self.instance.pk if self.instance.pk else None)

        if existing.exists():
            raise ValidationError(
                f'Vehicle with registration "{reg}" '
                f'is already registered in the system.'
            )
        return reg