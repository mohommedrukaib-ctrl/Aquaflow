"""
AquaFlow — Loyalty Services
Powered by Quantum Axis

Business logic layer for loyalty points.
Called from POS, refunds, admin adjustments, etc.
"""

from django.db import transaction
from .models import LoyaltyTransaction


def award_points(customer, points, tx_type, description='',
                 reference_id='', reference_type='', user=None):
    """
    Award or deduct loyalty points.
    Auto-wraps in transaction for safety.
    Returns new balance or None if invalid.
    """
    from apps.customers.models import Customer

    if not isinstance(customer, Customer):
        return None

    # Auto-wrap in transaction if not already in one
    with transaction.atomic():
        customer = Customer.objects.select_for_update().get(pk=customer.pk)
        new_balance = customer.loyalty_points + points

        if new_balance < 0:
            return None  # Cannot go negative

        customer.loyalty_points = new_balance
        customer.save(update_fields=['loyalty_points', 'updated_at'])

        LoyaltyTransaction.objects.create(
            customer         = customer,
            transaction_type = tx_type,
            points           = points,
            balance_after    = new_balance,
            reference_id     = reference_id,
            reference_type   = reference_type,
            description      = description,
            created_by       = user,
        )

    return new_balance