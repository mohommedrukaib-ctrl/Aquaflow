"""
AquaFlow — Customer Forms
Powered by Quantum Axis
"""

from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):

    class Meta:
        model  = Customer
        fields = [
            'name', 'phone', 'phone2',
            'email', 'address', 'notes', 'status',
        ]
        widgets = {
            'name':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'phone':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Primary phone'}),
            'phone2':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Secondary phone'}),
            'email':   forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notes':   forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status':  forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError('Name must be at least 2 characters.')
        return name

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone:
            raise forms.ValidationError('Phone number is required.')
        return phone