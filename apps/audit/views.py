"""
AquaFlow — Audit Log Views
Powered by Quantum Axis

Immutable audit trail. Never delete.
Only Super Admin, Owner, and users with AUDIT_VIEW permission.
"""

import csv
import logging
import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import PermissionCode
from apps.system.models import AuditLog

logger = logging.getLogger('apps')


def check_permission(request, code):
    try:
        return request.user.profile.has_permission(code)
    except Exception:
        return False


# ─── AUDIT LOG LIST ──────────────────────────────────────────

@login_required
def audit_list(request):
    if not check_permission(request, PermissionCode.AUDIT_VIEW):
        messages.error(request, 'Only Super Admin or Owner can view audit logs.')
        return redirect('dashboard')

    search    = request.GET.get('q', '').strip()
    user_id   = request.GET.get('user', '')
    action    = request.GET.get('action', '')
    module    = request.GET.get('module', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')

    logs = AuditLog.objects.select_related('user').all()

    if search:
        logs = logs.filter(
            Q(action__icontains=search) |
            Q(module__icontains=search) |
            Q(object_repr__icontains=search) |
            Q(user_name_snapshot__icontains=search) |
            Q(ip_address__icontains=search)
        )
    if user_id:
        logs = logs.filter(user_id=user_id)
    if action:
        logs = logs.filter(action=action)
    if module:
        logs = logs.filter(module=module)
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)

    logs = logs.order_by('-timestamp')

    total_count = logs.count()

    # Distinct filter options
    all_actions = AuditLog.objects.values_list('action', flat=True).distinct().order_by('action')
    all_modules = AuditLog.objects.values_list('module', flat=True).distinct().order_by('module')
    all_users   = User.objects.filter(is_active=True).order_by('username')

    paginator = Paginator(logs, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title':  'Audit Logs',
        'page_obj':    page_obj,
        'logs':        page_obj,
        'search':      search,
        'user_id':     user_id,
        'action':      action,
        'module':      module,
        'date_from':   date_from,
        'date_to':     date_to,
        'total_count': total_count,
        'all_actions': all_actions,
        'all_modules': all_modules,
        'all_users':   all_users,
    }
    return render(request, 'audit/audit_list.html', context)


# ─── AUDIT DETAIL ────────────────────────────────────────────

@login_required
def audit_detail(request, pk):
    if not check_permission(request, PermissionCode.AUDIT_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    log = get_object_or_404(AuditLog.objects.select_related('user'), pk=pk)

    # Format JSON data for display
    prev_data = ''
    new_data  = ''
    if log.previous_data:
        try:
            prev_data = json.dumps(log.previous_data, indent=2, ensure_ascii=False)
        except Exception:
            prev_data = str(log.previous_data)
    if log.new_data:
        try:
            new_data = json.dumps(log.new_data, indent=2, ensure_ascii=False)
        except Exception:
            new_data = str(log.new_data)

    context = {
        'page_title': f'Audit — {log.action}',
        'log':        log,
        'prev_data':  prev_data,
        'new_data':   new_data,
    }
    return render(request, 'audit/audit_detail.html', context)


# ─── AUDIT DASHBOARD ─────────────────────────────────────────

@login_required
def audit_dashboard(request):
    if not check_permission(request, PermissionCode.AUDIT_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    now = timezone.now()
    today = now.date()
    week_ago = today - timedelta(days=7)

    total_logs   = AuditLog.objects.count()
    today_logs   = AuditLog.objects.filter(timestamp__date=today).count()
    week_logs    = AuditLog.objects.filter(timestamp__date__gte=week_ago).count()
    active_users = AuditLog.objects.filter(
        timestamp__date=today
    ).values('user').distinct().count()

    # Top actions this week
    top_actions = AuditLog.objects.filter(
        timestamp__date__gte=week_ago,
    ).values('action').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    # Top users this week
    top_users = AuditLog.objects.filter(
        timestamp__date__gte=week_ago,
    ).exclude(user__isnull=True).values(
        'user__username', 'user_name_snapshot'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    # Top modules this week
    top_modules = AuditLog.objects.filter(
        timestamp__date__gte=week_ago,
    ).values('module').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    # Recent critical actions
    critical_actions = [
        'ORDER_VOIDED', 'PAYMENT_REFUNDED', 'ITEM_PURGED',
        'PRODUCT_DELETED', 'CUSTOMER_DELETED', 'VEHICLE_DELETED',
        'SERVICE_DELETED', 'STOCK_ADJUSTED',
    ]
    recent_critical = AuditLog.objects.filter(
        action__in=critical_actions,
    ).select_related('user').order_by('-timestamp')[:10]

    context = {
        'page_title':      'Audit Dashboard',
        'total_logs':      total_logs,
        'today_logs':      today_logs,
        'week_logs':       week_logs,
        'active_users':    active_users,
        'top_actions':     top_actions,
        'top_users':       top_users,
        'top_modules':     top_modules,
        'recent_critical': recent_critical,
    }
    return render(request, 'audit/audit_dashboard.html', context)


# ─── EXPORT CSV ──────────────────────────────────────────────

@login_required
def audit_export_csv(request):
    if not check_permission(request, PermissionCode.AUDIT_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    # Apply same filters as list view
    search    = request.GET.get('q', '').strip()
    user_id   = request.GET.get('user', '')
    action    = request.GET.get('action', '')
    module    = request.GET.get('module', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')

    logs = AuditLog.objects.select_related('user')

    if search:
        logs = logs.filter(
            Q(action__icontains=search) |
            Q(module__icontains=search) |
            Q(object_repr__icontains=search) |
            Q(user_name_snapshot__icontains=search)
        )
    if user_id:
        logs = logs.filter(user_id=user_id)
    if action:
        logs = logs.filter(action=action)
    if module:
        logs = logs.filter(module=module)
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)

    logs = logs.order_by('-timestamp')[:10000]  # Max 10k records

    response = HttpResponse(content_type='text/csv')
    filename = f'audit_log_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Timestamp', 'User', 'Action', 'Module',
        'Object Type', 'Object ID', 'Object', 'IP Address',
        'Previous Data', 'New Data',
    ])

    for log in logs:
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.user_name_snapshot or (log.user.username if log.user else ''),
            log.action,
            log.module,
            log.object_type,
            log.object_id,
            log.object_repr,
            log.ip_address or '',
            json.dumps(log.previous_data) if log.previous_data else '',
            json.dumps(log.new_data) if log.new_data else '',
        ])

    return response