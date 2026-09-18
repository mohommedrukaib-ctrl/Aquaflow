"""
AquaFlow Template Tags
Powered by Quantum Axis

Usage in templates:
    {% load aquaflow_tags %}
    {{ amount|currency }}
    {{ amount|currency:business.currency_symbol }}
"""

from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter
def currency(value, symbol='Rs.'):
    """
    Format a decimal value as currency.
    Example: {{ order.total|currency }}  →  Rs. 2,500.00
    """
    try:
        amount = Decimal(str(value))
        formatted = f'{amount:,.2f}'
        return f'{symbol} {formatted}'
    except (InvalidOperation, TypeError, ValueError):
        return f'{symbol} 0.00'


@register.filter
def currency_plain(value):
    """
    Format without symbol.
    Example: {{ order.total|currency_plain }}  →  2,500.00
    """
    try:
        amount = Decimal(str(value))
        return f'{amount:,.2f}'
    except (InvalidOperation, TypeError, ValueError):
        return '0.00'


@register.simple_tag(takes_context=True)
def format_currency(context, value):
    """
    Format using the business currency symbol from context.
    Example: {% format_currency order.total %}
    """
    symbol = context.get('CURRENCY_SYMBOL', 'Rs.')
    return currency(value, symbol)


@register.filter
def status_badge(status):
    """
    Returns Bootstrap badge class for a status string.
    """
    mapping = {
        'active':       'success',
        'inactive':     'secondary',
        'pending':      'warning',
        'confirmed':    'info',
        'completed':    'primary',
        'cancelled':    'danger',
        'waiting':      'warning',
        'washing':      'info',
        'ready':        'success',
        'paid':         'success',
        'unpaid':       'danger',
        'partial':      'warning',
        'void':         'dark',
        'draft':        'secondary',
    }
    css = mapping.get(str(status).lower(), 'secondary')
    return f'badge bg-{css}'