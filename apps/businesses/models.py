"""
AquaFlow — Business Model
Powered by Quantum Axis

The business using the software.
Completely separate from Quantum Axis developer branding.
Business name, logo, address are all configurable by Super Admin.
"""

from django.db import models
from django.utils import timezone


class Business(models.Model):
    """
    The car wash business using AquaFlow.
    One business per installation in V1.
    Multi-business support in future versions.
    """

    # ─── Identity ─────────────────────────────────────────────
    name = models.CharField(
        max_length=255,
        default='Your Business Name',
        help_text='Business trading name displayed on receipts and UI.',
    )
    legal_name = models.CharField(
        max_length=255,
        blank=True,
        help_text='Legal registered business name.',
    )
    registration_number = models.CharField(
        max_length=100,
        blank=True,
        help_text='Business registration number.',
    )

    # ─── Contact ──────────────────────────────────────────────
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city          = models.CharField(max_length=100, blank=True)
    state         = models.CharField(max_length=100, blank=True)
    postal_code   = models.CharField(max_length=20,  blank=True)
    country       = models.CharField(
        max_length=100,
        default='Sri Lanka',
    )
    phone         = models.CharField(max_length=50, blank=True)
    phone2        = models.CharField(max_length=50, blank=True)
    email         = models.EmailField(blank=True)
    website       = models.URLField(blank=True)

    # ─── Branding ─────────────────────────────────────────────
    logo = models.ImageField(
        upload_to='logos/',
        null=True,
        blank=True,
        help_text='Business logo. Displayed on receipts and UI.',
    )
    tagline = models.CharField(
        max_length=255,
        blank=True,
        help_text='Short tagline shown on receipts.',
    )

    # ─── Currency ─────────────────────────────────────────────
    currency_code = models.CharField(
        max_length=10,
        default='LKR',
        help_text='ISO 4217 currency code. Default: LKR',
    )
    currency_symbol = models.CharField(
        max_length=10,
        default='Rs.',
        help_text='Currency symbol for display. Default: Rs.',
    )
    currency_name = models.CharField(
        max_length=100,
        default='Sri Lankan Rupee',
    )

    # ─── Locale ───────────────────────────────────────────────
    timezone = models.CharField(
        max_length=100,
        default='Asia/Colombo',
    )
    date_format = models.CharField(
        max_length=50,
        default='%d %b %Y',
        help_text='Python date format string.',
    )
    time_format = models.CharField(
        max_length=50,
        default='%I:%M %p',
    )

    # ─── Print / Receipt ──────────────────────────────────────
    print_format = models.CharField(
        max_length=50,
        default='thermal_80mm',
        choices=[
            ('thermal_80mm', 'Thermal Receipt (80mm)'),
            ('dot_matrix',   'Dot Matrix'),
            ('half_a4',      'Half A4'),
            ('a4',           'A4'),
        ],
        help_text='Default print format for receipts and invoices.',
    )
    receipt_footer = models.TextField(
        blank=True,
        help_text='Text printed at the bottom of every receipt.',
        default='Thank you for choosing us!',
    )
    show_tax_on_receipt  = models.BooleanField(default=True)
    show_logo_on_receipt = models.BooleanField(default=True)

    # ─── Tax ──────────────────────────────────────────────────
    tax_enabled      = models.BooleanField(default=False)
    tax_name         = models.CharField(
        max_length=50,
        default='VAT',
        blank=True,
    )
    tax_percentage   = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    tax_number       = models.CharField(max_length=100, blank=True)

    # ─── Status ───────────────────────────────────────────────
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

        # Job Note settings
    job_note_format = models.CharField(
        max_length=50,
        default='thermal_80mm',
        choices=[
            ('thermal_80mm', 'Thermal Receipt (80mm)'),
            ('half_a4_bw',   'Half A4 (Black & White)'),
        ],
        help_text='Default format for Job Notes.',
    )
    job_note_message = models.TextField(
        blank=True,
        default='Please present this note when collecting your vehicle.',
        help_text='Message printed on job notes.',
    )
    job_note_terms = models.TextField(
        blank=True,
        default='We are not responsible for items left inside the vehicle.',
        help_text='Terms & conditions on job notes.',
    )

    class Meta:
        db_table    = 'businesses'
        verbose_name        = 'Business'
        verbose_name_plural = 'Businesses'

    def __str__(self):
        return self.name

    @property
    def full_address(self):
        parts = filter(None, [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country,
        ])
        return ', '.join(parts)

    @classmethod
    def get_default(cls):
        """
        Returns the primary business instance.
        Creates a default one if none exists.
        """
        business, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'name':            'Your Business Name',
                'currency_code':   'LKR',
                'currency_symbol': 'Rs.',
                'currency_name':   'Sri Lankan Rupee',
                'timezone':        'Asia/Colombo',
                'country':         'Sri Lanka',
            }
        )
        return business