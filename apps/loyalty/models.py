"""
AquaFlow — Loyalty Points Models
Powered by Quantum Axis
"""

from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class LoyaltyConfig(models.Model):
    """Single-row configuration for loyalty program."""

    is_enabled = models.BooleanField(default=True)

    points_per_currency = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
        help_text='Points earned per Rs. 100 spent.',
    )
    currency_per_point = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
        help_text='Rupees value per point when redeeming.',
    )
    min_points_to_redeem = models.PositiveIntegerField(
        default=100,
        help_text='Minimum points required to redeem.',
    )
    max_redemption_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=50,
        help_text='Max % of total that can be paid with points.',
    )
    points_expiry_days = models.PositiveIntegerField(
        default=365,
        help_text='Points expire after this many days. 0 = never.',
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loyalty_config'

    def __str__(self):
        return 'Loyalty Configuration'

    @classmethod
    def get_config(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class LoyaltyTransaction(models.Model):

    TYPE_EARN    = 'earn'
    TYPE_REDEEM  = 'redeem'
    TYPE_ADJUST  = 'adjust'
    TYPE_EXPIRE  = 'expire'
    TYPE_BONUS   = 'bonus'

    TYPE_CHOICES = [
        (TYPE_EARN,   'Earned'),
        (TYPE_REDEEM, 'Redeemed'),
        (TYPE_ADJUST, 'Adjustment'),
        (TYPE_EXPIRE, 'Expired'),
        (TYPE_BONUS,  'Bonus'),
    ]

    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='loyalty_transactions',
    )
    transaction_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, db_index=True,
    )
    points = models.IntegerField(
        help_text='Positive to earn, negative to redeem.',
    )
    balance_after = models.IntegerField(default=0)

    reference_id   = models.CharField(max_length=100, blank=True)
    reference_type = models.CharField(max_length=50, blank=True)
    description    = models.CharField(max_length=255, blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'loyalty_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', '-created_at']),
        ]

    def __str__(self):
        sign = '+' if self.points > 0 else ''
        return f'{self.customer.name}: {sign}{self.points} pts'