"""
AquaFlow — Invoice Views
Powered by Quantum Axis
"""

import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from .models import Invoice
from apps.accounts.models import PermissionCode

logger = logging.getLogger('apps')


def check_permission(request, code):
    try:
        return request.user.profile.has_permission(code)
    except Exception:
        return False


@login_required
def invoice_list(request):
    if not check_permission(request, PermissionCode.INVOICES_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    invoices = Invoice.objects.select_related(
        'order', 'order__customer', 'order__vehicle', 'order__branch',
    )

    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search) |
            Q(order__customer__name__icontains=search) |
            Q(order__vehicle__registration_number__icontains=search)
        )

    if status:
        invoices = invoices.filter(status=status)

    if date_from:
        invoices = invoices.filter(created_at__date__gte=date_from)
    if date_to:
        invoices = invoices.filter(created_at__date__lte=date_to)

    invoices = invoices.order_by('-created_at')

    total_count = invoices.count()
    total_amount = invoices.aggregate(Sum('total'))['total__sum'] or 0

    paginator = Paginator(invoices, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title':   'Invoices',
        'page_obj':     page_obj,
        'invoices':     page_obj,
        'search':       search,
        'status':       status,
        'date_from':    date_from,
        'date_to':      date_to,
        'total_count':  total_count,
        'total_amount': total_amount,
        'status_choices': Invoice.STATUS_CHOICES,
    }
    return render(request, 'invoices/invoice_list.html', context)


@login_required
def invoice_detail(request, pk):
    if not check_permission(request, PermissionCode.INVOICES_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    invoice = get_object_or_404(
        Invoice.objects.select_related(
            'order', 'order__customer', 'order__vehicle', 'order__branch',
        ).prefetch_related('items', 'payments__payment_method'),
        pk=pk
    )

    context = {
        'page_title': invoice.invoice_number,
        'invoice':    invoice,
        'order':      invoice.order,
        'items':      invoice.items.all(),
        'payments':   invoice.payments.all(),
    }
    return render(request, 'invoices/invoice_detail.html', context)