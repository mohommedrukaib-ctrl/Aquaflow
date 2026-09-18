"""
AquaFlow — Business Settings Views
Powered by Quantum Axis
"""

import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import Business
from apps.accounts.models import PermissionCode
from apps.system.models import AuditLog

logger = logging.getLogger('apps')


def check_permission(request, code):
    try:
        return request.user.profile.has_permission(code)
    except Exception:
        return False


def client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@login_required
def business_settings(request):
    if not check_permission(request, PermissionCode.BUSINESS_CONFIGURE):
        messages.error(request, 'Only Super Admin or Owner can edit business settings.')
        return redirect('dashboard')

    business = Business.get_default()

    if request.method == 'POST':
        try:
            # Text fields
            business.name           = request.POST.get('name', '').strip() or 'Your Business Name'
            business.legal_name     = request.POST.get('legal_name', '').strip()
            business.registration_number = request.POST.get('registration_number', '').strip()
            business.tagline        = request.POST.get('tagline', '').strip()

            # Address
            business.address_line1  = request.POST.get('address_line1', '').strip()
            business.address_line2  = request.POST.get('address_line2', '').strip()
            business.city           = request.POST.get('city', '').strip()
            business.state          = request.POST.get('state', '').strip()
            business.postal_code    = request.POST.get('postal_code', '').strip()
            business.country        = request.POST.get('country', '').strip() or 'Sri Lanka'

            # Contact
            business.phone          = request.POST.get('phone', '').strip()
            business.phone2         = request.POST.get('phone2', '').strip()
            business.email          = request.POST.get('email', '').strip()
            business.website        = request.POST.get('website', '').strip()

            # Currency
            business.currency_code   = request.POST.get('currency_code', 'LKR').strip().upper()
            business.currency_symbol = request.POST.get('currency_symbol', 'Rs.').strip()
            business.currency_name   = request.POST.get('currency_name', '').strip() or 'Sri Lankan Rupee'

            # Locale
            business.timezone       = request.POST.get('timezone', 'Asia/Colombo').strip()

            # Print
            business.print_format   = request.POST.get('print_format', 'thermal_80mm').strip()
            business.receipt_footer = request.POST.get('receipt_footer', '').strip()
            business.show_tax_on_receipt = request.POST.get('show_tax_on_receipt') == 'true'
            business.show_logo_on_receipt = request.POST.get('show_logo_on_receipt') == 'true'

            # Tax
            business.tax_enabled    = request.POST.get('tax_enabled') == 'true'
            business.tax_name       = request.POST.get('tax_name', 'VAT').strip()
            try:
                pct = Decimal(request.POST.get('tax_percentage', '0'))
                if pct < 0 or pct > 100:
                    pct = Decimal('0')
                business.tax_percentage = pct
            except (InvalidOperation, ValueError):
                business.tax_percentage = Decimal('0')
            business.tax_number     = request.POST.get('tax_number', '').strip()

            # Logo upload
            if 'logo' in request.FILES:
                # Delete old logo file if exists
                if business.logo:
                    try:
                        business.logo.delete(save=False)
                    except Exception:
                        pass
                business.logo = request.FILES['logo']

            # Delete logo checkbox
            if request.POST.get('delete_logo') == 'true' and business.logo:
                try:
                    business.logo.delete(save=False)
                except Exception:
                    pass
                business.logo = None

            business.save()

            AuditLog.log(
                action='BUSINESS_UPDATED',
                module='businesses',
                user=request.user,
                object_type='Business',
                object_id=business.pk,
                object_repr=business.name,
                new_data={
                    'name': business.name,
                    'currency': business.currency_code,
                    'tax_enabled': business.tax_enabled,
                    'tax_percentage': str(business.tax_percentage),
                },
                ip_address=client_ip(request),
            )

            messages.success(request, '✓ Business settings saved successfully.')
            return redirect('business_settings')

        except Exception as e:
            logger.exception('Business save failed')
            messages.error(request, f'Failed to save: {e}')

    context = {
        'page_title': 'Business Settings',
        'business':   business,
        'print_formats': [
            ('thermal_80mm', 'Thermal Receipt (80mm)'),
            ('dot_matrix',   'Dot Matrix'),
            ('half_a4',      'Half A4'),
            ('a4',           'A4'),
        ],
        'currencies': [
            ('LKR', 'Rs.', 'Sri Lankan Rupee'),
            ('USD', '$',   'US Dollar'),
            ('EUR', '€',   'Euro'),
            ('GBP', '£',   'British Pound'),
            ('INR', '₹',   'Indian Rupee'),
            ('AED', 'د.إ', 'UAE Dirham'),
        ],
        'timezones': [
            'Asia/Colombo',
            'Asia/Dubai',
            'Asia/Kolkata',
            'Asia/Singapore',
            'Europe/London',
            'America/New_York',
            'UTC',
        ],
    }
    return render(request, 'businesses/settings.html', context)