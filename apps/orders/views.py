"""
AquaFlow — Order Views
Powered by Quantum Axis
"""

import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import Order
from apps.accounts.models import PermissionCode, RoleCode
from apps.system.models import AuditLog

logger = logging.getLogger('apps')


def check_permission(request, code):
    try:
        return request.user.profile.has_permission(code)
    except Exception:
        return False


def is_super_admin(request):
    try:
        return request.user.profile.role.code == RoleCode.SUPER_ADMIN
    except Exception:
        return False


def client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ─── ORDER LIST ──────────────────────────────────────────────

@login_required
def order_list(request):
    if not check_permission(request, PermissionCode.ORDERS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    search    = request.GET.get('q', '').strip()
    status    = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')

    orders = Order.objects.select_related(
        'customer', 'vehicle', 'branch', 'created_by'
    )

    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(customer__phone__icontains=search) |
            Q(vehicle__registration_number__icontains=search)
        )

    if status:
        orders = orders.filter(status=status)

    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    orders = orders.order_by('-created_at')

    # Stats
    total_count  = orders.count()
    total_amount = orders.aggregate(Sum('total'))['total__sum'] or 0

    paginator = Paginator(orders, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title':     'Orders',
        'page_obj':       page_obj,
        'orders':         page_obj,
        'search':         search,
        'status':         status,
        'date_from':      date_from,
        'date_to':        date_to,
        'total_count':    total_count,
        'total_amount':   total_amount,
        'status_choices': Order.STATUS_CHOICES,
        'can_void':       is_super_admin(request),
    }
    return render(request, 'orders/order_list.html', context)

# ─── ORDER DETAIL ────────────────────────────────────────────

@login_required
def order_detail(request, pk):
    if not check_permission(request, PermissionCode.ORDERS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    order = get_object_or_404(
        Order.objects.select_related(
            'customer', 'vehicle', 'branch', 'created_by',
            'booking', 'invoice',
        ),
        pk=pk
    )

    # Get invoice items
    items = []
    if hasattr(order, 'invoice'):
        items = order.invoice.items.all()

    # Get payments
    payments = []
    if hasattr(order, 'invoice'):
        payments = order.invoice.payments.select_related('payment_method').all()

    context = {
        'page_title': order.order_number,
        'order':      order,
        'items':      items,
        'payments':   payments,
        'can_void':   is_super_admin(request),
        'can_refund': check_permission(request, PermissionCode.POS_REFUND),
    }
    return render(request, 'orders/order_detail.html', context)


# ─── VOID ORDER (Super Admin only) ───────────────────────────

@login_required
@require_http_methods(['POST'])
def order_void(request, pk):
    if not is_super_admin(request):
        return JsonResponse({
            'success': False,
            'error': 'Only Super Admin can void orders.',
        }, status=403)

    order = get_object_or_404(Order, pk=pk)

    if order.status == Order.STATUS_VOID:
        return JsonResponse({
            'success': False,
            'error': 'Order is already void.',
        }, status=400)

    reason = request.POST.get('reason', '').strip()
    if not reason:
        return JsonResponse({
            'success': False,
            'error': 'Void reason is required.',
        }, status=400)

    try:
        with transaction.atomic():
            previous_status = order.status
            order.status = Order.STATUS_VOID
            order.payment_status = Order.PAYMENT_VOID
            order.notes = (order.notes or '') + f'\n[VOIDED] {reason}'
            order.save()

            # Void invoice
            if hasattr(order, 'invoice'):
                order.invoice.status = 'void'
                order.invoice.save()

            AuditLog.log(
                action='ORDER_VOIDED',
                module='orders',
                user=request.user,
                object_type='Order',
                object_id=order.pk,
                object_repr=order.order_number,
                previous_data={'status': previous_status},
                new_data={'status': order.status, 'reason': reason},
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'Order {order.order_number} has been voided.',
        })
    except Exception as e:
        logger.exception('Order void failed')
        return JsonResponse({
            'success': False,
            'error': f'Void failed: {e}',
        }, status=500)