"""
AquaFlow Global Context Processor
Powered by Quantum Axis

Loads business settings from database.
Available in ALL templates automatically.
"""

from django.conf import settings
import logging

logger = logging.getLogger('apps')


def aquaflow_context(request):
    """
    Injects business info, currency and system info
    into every template. DB-first with settings fallback.
    """

    # ─── Defaults from settings ───────────────────────────────
    business_name    = 'Your Business Name'
    business_address = ''
    business_phone   = ''
    business_email   = ''
    business_logo    = None
    currency_code    = settings.DEFAULT_CURRENCY_CODE
    currency_symbol  = settings.DEFAULT_CURRENCY_SYMBOL
    currency_name    = settings.DEFAULT_CURRENCY_NAME
    print_format     = 'thermal_80mm'
    tax_enabled      = False
    tax_name         = 'VAT'
    tax_percentage   = 0

    # ─── Load from database ───────────────────────────────────
    try:
        from apps.businesses.models import Business
        business = Business.objects.filter(pk=1).first()
        if business:
            business_name    = business.name
            business_address = business.full_address
            business_phone   = business.phone
            business_email   = business.email
            business_logo    = business.logo.url if business.logo else None
            currency_code    = business.currency_code
            currency_symbol  = business.currency_symbol
            currency_name    = business.currency_name
            print_format     = business.print_format
            tax_enabled      = business.tax_enabled
            tax_name         = business.tax_name
            tax_percentage   = business.tax_percentage
    except Exception as e:
        # DB may not be ready during migrations
        logger.debug(f'Context processor DB load skipped: {e}')

    return {
        # ─── Developer / System ───────────────────────────────
        'AQUAFLOW_DEVELOPER':   settings.AQUAFLOW_DEVELOPER,
        'AQUAFLOW_VERSION':     settings.AQUAFLOW_VERSION,
        'AQUAFLOW_SYSTEM_NAME': settings.AQUAFLOW_SYSTEM_NAME,

        # ─── Business ─────────────────────────────────────────
        'BUSINESS_NAME':    business_name,
        'BUSINESS_ADDRESS': business_address,
        'BUSINESS_PHONE':   business_phone,
        'BUSINESS_EMAIL':   business_email,
        'BUSINESS_LOGO':    business_logo,

        # ─── Currency ─────────────────────────────────────────
        'CURRENCY_CODE':    currency_code,
        'CURRENCY_SYMBOL':  currency_symbol,
        'CURRENCY_NAME':    currency_name,

        # ─── Print ────────────────────────────────────────────
        'PRINT_FORMAT':     print_format,

        # ─── Tax ──────────────────────────────────────────────
        'TAX_ENABLED':      tax_enabled,
        'TAX_NAME':         tax_name,
        'TAX_PERCENTAGE':   tax_percentage,
    }