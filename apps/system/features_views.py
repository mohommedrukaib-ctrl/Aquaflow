"""
AquaFlow — Feature Flag Management Views
Powered by Quantum Axis
"""

import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.accounts.models import RoleCode
from apps.system.models import SystemSetting, AuditLog
from apps.system.features import (
    FEATURE_GROUPS,
    FEATURES as FEATURE_KEYS,
    is_feature_enabled,
    invalidate_feature_cache,
)

logger = logging.getLogger('apps')


def is_super_admin(request):
    try:
        return request.user.profile.role.code == RoleCode.SUPER_ADMIN
    except Exception:
        return False


@login_required
def manage_features(request):
    """Super Admin — feature toggle page with grouped sections."""
    if not is_super_admin(request):
        messages.error(request, 'Only Super Admin can configure features.')
        return redirect('dashboard')

    grouped_features = []

    for group_name, group_items in FEATURE_GROUPS.items():
        features_in_group = []
        for key, label in group_items.items():
            features_in_group.append({
                'key': key,
                'name': label,
                'enabled': is_feature_enabled(key),
            })
        grouped_features.append({
            'group': group_name,
            'items': features_in_group,
        })

    total = len(FEATURE_KEYS)
    enabled_count = sum(
        1 for k in FEATURE_KEYS if is_feature_enabled(k)
    )

    context = {
        'page_title':     'Feature Configuration',
        'feature_groups': grouped_features,
        'total_features': total,
        'enabled_count':  enabled_count,
        'disabled_count': total - enabled_count,
        'breadcrumbs': [
            {'label': 'System',   'url': '/system/'},
            {'label': 'Features', 'url': None},
        ],
    }
    return render(request, 'system/features.html', context)


@login_required
@require_http_methods(['POST'])
def toggle_feature_ajax(request):
    """AJAX toggle — flips one feature on/off."""
    if not is_super_admin(request):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'},
            status=403,
        )

    feature_key = request.POST.get('feature_key', '').strip()
    enabled_raw = request.POST.get('enabled', '')
    enabled = enabled_raw == 'true'

    if feature_key not in FEATURE_KEYS:
        return JsonResponse(
            {'success': False, 'error': 'Invalid feature key.'},
            status=400,
        )

    try:
        setting_key = f'feature.{feature_key}'
        value_str = 'on' if enabled else 'off'

        setting, _ = SystemSetting.objects.get_or_create(
            key=setting_key,
            defaults={
                'is_sensitive': False,
                'description': f'Feature flag: {feature_key}',
            },
        )

        previous_value = setting.value
        setting.value = value_str
        setting.save()

        invalidate_feature_cache(feature_key)

        AuditLog.log(
            action='FEATURE_TOGGLED',
            module='system',
            user=request.user,
            object_type='SystemSetting',
            object_id=setting.pk,
            object_repr=f'{FEATURE_KEYS[feature_key]} → {value_str.upper()}',
            previous_data={'enabled': previous_value == 'on'},
            new_data={'enabled': enabled},
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        label = FEATURE_KEYS[feature_key]
        state = 'ENABLED' if enabled else 'DISABLED'

        return JsonResponse({
            'success': True,
            'message': f'"{label}" is now {state}.',
            'enabled': enabled,
        })

    except Exception as e:
        logger.exception('Feature toggle failed')
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=500,
        )


@login_required
@require_http_methods(['POST'])
def bulk_toggle_features(request):
    """Toggle all features in a group at once."""
    if not is_super_admin(request):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'},
            status=403,
        )

    action = request.POST.get('action', '')  # 'all_on' or 'all_off'

    if action not in ('all_on', 'all_off'):
        return JsonResponse(
            {'success': False, 'error': 'Invalid action.'},
            status=400,
        )

    value_str = 'on' if action == 'all_on' else 'off'
    enabled = action == 'all_on'

    toggled = []

    for key, label in FEATURE_KEYS.items():
        setting, _ = SystemSetting.objects.get_or_create(
            key=f'feature.{key}',
            defaults={
                'is_sensitive': False,
                'description': f'Feature flag: {key}',
            },
        )
        setting.value = value_str
        setting.save()
        invalidate_feature_cache(key)
        toggled.append(label)

    AuditLog.log(
        action='FEATURES_BULK_TOGGLED',
        module='system',
        user=request.user,
        object_type='SystemSetting',
        new_data={
            'action': action,
            'value': value_str,
            'count': len(toggled),
        },
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    state = 'ENABLED' if enabled else 'DISABLED'
    return JsonResponse({
        'success': True,
        'message': f'All {len(toggled)} features {state}.',
    })