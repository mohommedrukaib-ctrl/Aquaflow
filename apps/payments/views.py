"""
AquaFlow — Payment Views
Powered by Quantum Axis
"""

import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import Payment, PaymentMethod
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


# ─── PAYMENT LIST ────────────────────────────────────────────

@login_required
def payment_list(request):
    if not check_permission(request, PermissionCode.INVOICES_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    search = request.GET.get('q', '').strip()
    method = request.GET.get('method', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    payments = Payment.objects.select_related(
        'invoice', 'order', 'payment_method', 'processed_by',
        'order__customer',
    )

    if search:
        payments = payments.filter(
            Q(invoice__invoice_number__icontains=search) |
            Q(order__order_number__icontains=search) |
            Q(reference__icontains=search) |
            Q(order__customer__name__icontains=search)
        )
    if method:
        payments = payments.filter(payment_method_id=method)
    if date_from:
        payments = payments.filter(processed_at__date__gte=date_from)
    if date_to:
        payments = payments.filter(processed_at__date__lte=date_to)

    payments = payments.order_by('-processed_at')

    total_amount = payments.aggregate(Sum('amount'))['amount__sum'] or 0

    paginator = Paginator(payments, 30)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title':      'Payments',
        'page_obj':        page_obj,
        'payments':        page_obj,
        'search':          search,
        'method':          method,
        'date_from':       date_from,
        'date_to':         date_to,
        'total_count':     paginator.count,
        'total_amount':    total_amount,
        'payment_methods': PaymentMethod.objects.filter(is_active=True),
    }
    return render(request, 'payments/payment_list.html', context)


# ─── DAILY SALES SUMMARY ─────────────────────────────────────

@login_required
def sales_summary(request):
    if not check_permission(request, PermissionCode.REPORTS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    date_str = request.GET.get('date', '')
    if date_str:
        try:
            target_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        except Exception:
            target_date = timezone.now().date()
    else:
        target_date = timezone.now().date()

    # All completed payments today
    payments = Payment.objects.filter(
        processed_at__date=target_date,
        status=Payment.STATUS_COMPLETED,
    ).select_related('payment_method', 'order__customer', 'processed_by')

    # By payment method
    by_method = payments.values(
        'payment_method__name', 'payment_method__code'
    ).annotate(
        total=Sum('amount'),
        count=Count('id'),
    ).order_by('-total')

    # By cashier
    by_cashier = payments.values(
        'processed_by__username', 'processed_by__first_name', 'processed_by__last_name'
    ).annotate(
        total=Sum('amount'),
        count=Count('id'),
    ).order_by('-total')

    # Total
    grand_total = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    total_count = payments.count()

    # Order stats
    from apps.orders.models import Order
    orders_today = Order.objects.filter(
        created_at__date=target_date,
    )
    orders_count = orders_today.count()
    voided_count = orders_today.filter(status=Order.STATUS_VOID).count()

    context = {
        'page_title':   f'Sales Summary — {target_date}',
        'target_date':  target_date,
        'grand_total':  grand_total,
        'total_count':  total_count,
        'orders_count': orders_count,
        'voided_count': voided_count,
        'by_method':    list(by_method),
        'by_cashier':   list(by_cashier),
    }
    return render(request, 'payments/sales_summary.html', context)


# ─── REFUND ──────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def process_refund(request, invoice_id):
    if not check_permission(request, PermissionCode.POS_REFUND):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    from apps.invoices.models import Invoice
    from apps.orders.models import Order

    invoice = get_object_or_404(Invoice, pk=invoice_id)
    order = invoice.order

    try:
        amount = Decimal(str(request.POST.get('amount', '0')))
    except (InvalidOperation, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid amount.'}, status=400)

    method_id = request.POST.get('method_id')
    reason = request.POST.get('reason', '').strip()
    pin = request.POST.get('pin', '').strip()

    if amount <= 0:
        return JsonResponse({'success': False, 'error': 'Amount must be greater than 0.'}, status=400)

    if amount > invoice.total:
        return JsonResponse({'success': False, 'error': 'Refund exceeds invoice total.'}, status=400)

    if not reason:
        return JsonResponse({'success': False, 'error': 'Reason required.'}, status=400)

    # Simple PIN check — for now, hardcoded manager PIN
    # In production, store per-user manager PIN
    MANAGER_PIN = '1234'  # TODO: move to settings
    if pin != MANAGER_PIN:
        return JsonResponse({'success': False, 'error': 'Invalid manager PIN.'}, status=403)

    if not method_id:
        return JsonResponse({'success': False, 'error': 'Refund method required.'}, status=400)

    try:
        method = PaymentMethod.objects.get(pk=method_id, is_active=True)
    except PaymentMethod.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid payment method.'}, status=400)

    try:
        with transaction.atomic():
            # Create negative payment (refund)
            refund_payment = Payment.objects.create(
                invoice        = invoice,
                order          = order,
                payment_method = method,
                amount         = -amount,  # Negative
                reference      = f'REFUND: {reason[:50]}',
                status         = Payment.STATUS_REFUNDED,
                notes          = reason,
                processed_by   = request.user,
            )

            # Update order/invoice status
            if amount == invoice.total:
                order.payment_status = Order.PAYMENT_REFUNDED
                invoice.status = 'refunded' if hasattr(Invoice, 'STATUS_REFUNDED') else 'void'
            else:
                order.payment_status = Order.PAYMENT_PARTIAL

            order.save(update_fields=['payment_status', 'updated_at'])
            invoice.save(update_fields=['status', 'updated_at'])

            AuditLog.log(
                action='PAYMENT_REFUNDED',
                module='payments',
                user=request.user,
                object_type='Payment',
                object_id=refund_payment.pk,
                object_repr=f'Refund for {invoice.invoice_number}',
                new_data={
                    'invoice':     invoice.invoice_number,
                    'order':       order.order_number,
                    'amount':      str(amount),
                    'method':      method.name,
                    'reason':      reason,
                    'approved_by': request.user.username,
                },
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'Refund of Rs. {amount} processed.',
        })
    except Exception as e:
        logger.exception('Refund failed')
        return JsonResponse({'success': False, 'error': f'Failed: {e}'}, status=500)