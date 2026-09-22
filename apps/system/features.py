"""
AquaFlow — Central Feature Flags
Powered by Quantum Axis

Toggle modules ON/OFF per client deployment.
Only Super Admin (Developer) can change these.
"""

import logging
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.cache import cache

logger = logging.getLogger('apps')

# ─── Master Feature List (grouped for UI) ───────────────────

FEATURE_GROUPS = {
    'Operations': {
        'bookings':          'Bookings & Scheduling',
        'wash':              'Wash Operations Board',
        'wash_bays':         'Wash Bay Management',
        'repairs':           'Repair & Diagnostics',
        'job_notes':         'Job Note Printing',
    },
    'Sales & Products': {
        'products':          'Product Sales (POS)',
        'tax':               'Tax / VAT System',
        'purchase_orders':   'Supplier Purchases',
    },
    'People & Loyalty': {
        'employees':         'Employee Tracking',
        'memberships':       'Memberships Pack',
        'loyalty':           'Loyalty Points Program',
    },
    'Finance & Data': {
        'finance':           'Expenses & Finance',
        'reports':           'Reports & Analytics',
        'inventory':         'Inventory & Suppliers',
    },
}

# Flat dict for fast lookup
FEATURES = {}
for group_features in FEATURE_GROUPS.values():
    FEATURES.update(group_features)


def is_feature_enabled(feature_name):
    """
    Cached feature flag check.
    Defaults to True if anything fails.
    """
    if feature_name not in FEATURES:
        return True

    cache_key = f'aqa:feat:{feature_name}'
    status = cache.get(cache_key)

    if status is not None:
        return status == 'on'

    try:
        from apps.system.models import SystemSetting

        setting_key = f'feature.{feature_name}'

        setting, _ = SystemSetting.objects.get_or_create(
            key=setting_key,
            defaults={
                'value': 'on',
                'description': f'Feature flag: {FEATURES[feature_name]}',
                'is_sensitive': False,
            },
        )

        val = setting.value.strip().lower()
        cache.set(cache_key, val, timeout=3600)
        return val == 'on'

    except Exception as e:
        logger.debug(f'Feature flag check failed for {feature_name}: {e}')
        return True


def invalidate_feature_cache(feature_name):
    """Clear cached flag so next check reads DB."""
    cache_key = f'aqa:feat:{feature_name}'
    try:
        cache.delete(cache_key)
    except Exception:
        pass


def feature_required(feature_name):
    """
    View decorator.
    If feature is disabled → redirect back with alert message.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not is_feature_enabled(feature_name):
                label = FEATURES.get(feature_name, feature_name)
                messages.warning(
                    request,
                    f'⚠ Feature "{label}" is currently disabled. '
                    f'Contact your administrator to enable it.',
                )
                referer = request.META.get('HTTP_REFERER')
                if referer and request.build_absolute_uri() != referer:
                    return redirect(referer)
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator