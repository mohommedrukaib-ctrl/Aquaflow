"""
AquaFlow — Supplier & Purchase Views
Powered by Quantum Axis
"""

import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import Supplier, Purchase, PurchaseItem
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


# ─── SUPPLIER LIST ───────────────────────────────────────────

@login_required
def supplier_list(request):
    if not check_permission(request, PermissionCode.SUPPLIERS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    search = request.GET.get('q', '').strip()
    suppliers = Supplier.objects.filter(is_deleted=False)

    if search:
        suppliers = suppliers.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(email__icontains=search)
        )

    suppliers = suppliers.order_by('name')

    paginator = Paginator(suppliers, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title':  'Suppliers',
        'page_obj':    page_obj,
        'suppliers':   page_obj,
        'search':      search,
        'total_count': paginator.count,
        'can_manage':  check_permission(request, PermissionCode.SUPPLIERS_MANAGE),
    }
    return render(request, 'suppliers/supplier_list.html', context)


# ─── SUPPLIER DETAIL ─────────────────────────────────────────

@login_required
def supplier_detail(request, pk):
    if not check_permission(request, PermissionCode.SUPPLIERS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('supplier_list')

    supplier = get_object_or_404(Supplier, pk=pk, is_deleted=False)
    purchases = supplier.purchases.order_by('-purchase_date')[:20]

    context = {
        'page_title': supplier.name,
        'supplier':   supplier,
        'purchases':  purchases,
        'can_manage': check_permission(request, PermissionCode.SUPPLIERS_MANAGE),
    }
    return render(request, 'suppliers/supplier_detail.html', context)


# ─── AJAX: Create Supplier ───────────────────────────────────

@login_required
@require_http_methods(['POST'])
def supplier_create_ajax(request):
    if not check_permission(request, PermissionCode.SUPPLIERS_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    name = request.POST.get('name', '').strip()
    phone = request.POST.get('phone', '').strip()
    contact_person = request.POST.get('contact_person', '').strip()
    email = request.POST.get('email', '').strip()
    address = request.POST.get('address', '').strip()

    if not name:
        return JsonResponse({'success': False, 'error': 'Name required.'}, status=400)

    # Check duplicate
    existing = Supplier.objects.filter(name__iexact=name, is_deleted=False).first()
    if existing:
        return JsonResponse({
            'success': True,
            'item': {
                'id':    existing.pk,
                'label': existing.name,
                'name':  existing.name,
                'meta':  existing.phone or existing.contact_person,
            },
            'message': f'"{name}" already exists — selected.',
        })

    try:
        supplier = Supplier.objects.create(
            name=name,
            phone=phone,
            contact_person=contact_person,
            email=email,
            address=address,
            is_active=True,
            created_by=request.user,
        )

        AuditLog.log(
            action='SUPPLIER_CREATED',
            module='suppliers',
            user=request.user,
            object_type='Supplier',
            object_id=supplier.pk,
            object_repr=supplier.name,
            new_data={'name': name, 'phone': phone},
            ip_address=client_ip(request),
        )

        return JsonResponse({
            'success': True,
            'item': {
                'id':    supplier.pk,
                'label': supplier.name,
                'name':  supplier.name,
                'meta':  supplier.phone or supplier.contact_person,
            },
            'message': f'Supplier "{supplier.name}" added.',
        })
    except Exception as e:
        logger.exception('Supplier create failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─── AJAX: Supplier Search ───────────────────────────────────

@login_required
def supplier_search_ajax(request):
    q = request.GET.get('q', '').strip()
    show_all = request.GET.get('all', '') == '1'

    suppliers = Supplier.objects.filter(is_deleted=False, is_active=True)
    if q:
        suppliers = suppliers.filter(
            Q(name__icontains=q) | Q(phone__icontains=q)
        )

    limit = 30 if show_all else 15
    suppliers = suppliers.order_by('name')[:limit]

    data = [
        {
            'id':    s.pk,
            'label': s.name,
            'name':  s.name,
            'meta':  s.phone or s.contact_person,
        }
        for s in suppliers
    ]
    return JsonResponse({'suppliers': data})


# ─── AJAX: Inline Edit ───────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def supplier_inline_edit(request, pk):
    if not check_permission(request, PermissionCode.SUPPLIERS_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    supplier = get_object_or_404(Supplier, pk=pk, is_deleted=False)
    field = request.POST.get('field', '').strip()
    value = request.POST.get('value', '').strip()

    if field not in ['name', 'phone', 'contact_person', 'email']:
        return JsonResponse({'success': False, 'error': 'Invalid field.'}, status=400)

    previous = {field: getattr(supplier, field)}
    setattr(supplier, field, value)
    supplier.save(update_fields=[field, 'updated_at'])

    AuditLog.log(
        action='SUPPLIER_UPDATED',
        module='suppliers',
        user=request.user,
        object_type='Supplier',
        object_id=supplier.pk,
        object_repr=supplier.name,
        previous_data=previous,
        new_data={field: value},
        ip_address=client_ip(request),
    )

    return JsonResponse({'success': True, 'message': 'Updated.', 'value': value})


# ─── AJAX: Delete Supplier ───────────────────────────────────

@login_required
@require_http_methods(['POST'])
def supplier_delete(request, pk):
    if not check_permission(request, PermissionCode.SUPPLIERS_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    supplier = get_object_or_404(Supplier, pk=pk, is_deleted=False)

    if supplier.purchases.exists():
        return JsonResponse({
            'success': False,
            'error': f'Cannot delete — supplier has {supplier.purchases.count()} purchase(s).',
        }, status=400)

    supplier.is_deleted = True
    supplier.deleted_at = timezone.now()
    supplier.deleted_by = request.user
    supplier.save()

    return JsonResponse({
        'success': True,
        'message': f'Supplier "{supplier.name}" moved to trash.',
    })


# ─── PURCHASE LIST ───────────────────────────────────────────

@login_required
def purchase_list(request):
    if not check_permission(request, PermissionCode.SUPPLIERS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    search    = request.GET.get('q', '').strip()
    status    = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')

    purchases = Purchase.objects.select_related('supplier', 'branch', 'created_by')

    if search:
        purchases = purchases.filter(
            Q(purchase_number__icontains=search) |
            Q(supplier__name__icontains=search) |
            Q(invoice_ref__icontains=search)
        )
    if status:
        purchases = purchases.filter(status=status)
    if date_from:
        purchases = purchases.filter(purchase_date__gte=date_from)
    if date_to:
        purchases = purchases.filter(purchase_date__lte=date_to)

    purchases = purchases.order_by('-purchase_date', '-created_at')

    total_count  = purchases.count()
    total_amount = purchases.aggregate(Sum('total'))['total__sum'] or 0

    paginator = Paginator(purchases, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title':     'Purchases',
        'page_obj':       page_obj,
        'purchases':      page_obj,
        'search':         search,
        'status':         status,
        'date_from':      date_from,
        'date_to':        date_to,
        'total_count':    total_count,
        'total_amount':   total_amount,
        'status_choices': Purchase.STATUS_CHOICES,
        'can_manage':     check_permission(request, PermissionCode.SUPPLIERS_MANAGE),
    }
    return render(request, 'suppliers/purchase_list.html', context)


# ─── PURCHASE CREATE ─────────────────────────────────────────

@login_required
@require_http_methods(['GET', 'POST'])
def purchase_create(request):
    if not check_permission(request, PermissionCode.SUPPLIERS_MANAGE):
        messages.error(request, 'Permission denied.')
        return redirect('purchase_list')

    if request.method == 'POST':
        try:
            import json
            payload = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid data.'}, status=400)

        supplier_id   = payload.get('supplier_id')
        branch_id     = payload.get('branch_id')
        purchase_date = payload.get('purchase_date')
        invoice_ref   = payload.get('invoice_ref', '').strip()
        items         = payload.get('items', [])
        amount_paid   = Decimal(str(payload.get('amount_paid', '0')))
        notes         = payload.get('notes', '').strip()

        if not supplier_id:
            return JsonResponse({'success': False, 'error': 'Supplier required.'}, status=400)
        if not items:
            return JsonResponse({'success': False, 'error': 'At least one item required.'}, status=400)

        from apps.inventory.models import Product, InventoryStock, InventoryTransaction
        from apps.branches.models import Branch

        try:
            with transaction.atomic():
                supplier = Supplier.objects.get(pk=supplier_id)
                branch   = Branch.objects.get(pk=branch_id or 1)

                subtotal = Decimal('0')
                resolved_items = []

                for item in items:
                    product = Product.objects.get(pk=item['product_id'], is_deleted=False)
                    qty = Decimal(str(item.get('quantity', 0)))
                    unit_cost = Decimal(str(item.get('unit_cost', 0)))

                    if qty <= 0 or unit_cost < 0:
                        raise ValueError('Invalid quantity or cost.')

                    line_total = qty * unit_cost
                    subtotal += line_total

                    resolved_items.append({
                        'product': product,
                        'quantity': qty,
                        'unit_cost': unit_cost,
                        'total': line_total,
                    })

                grand_total = subtotal

                if amount_paid < 0 or amount_paid > grand_total:
                    amount_paid = Decimal('0')

                payment_status = Purchase.PAYMENT_UNPAID
                if amount_paid >= grand_total:
                    payment_status = Purchase.PAYMENT_PAID
                elif amount_paid > 0:
                    payment_status = Purchase.PAYMENT_PARTIAL

                purchase = Purchase.objects.create(
                    supplier       = supplier,
                    branch         = branch,
                    purchase_date  = purchase_date or timezone.now().date(),
                    invoice_ref    = invoice_ref,
                    subtotal       = subtotal,
                    total          = grand_total,
                    amount_paid    = amount_paid,
                    status         = Purchase.STATUS_RECEIVED,
                    payment_status = payment_status,
                    notes          = notes,
                    created_by     = request.user,
                )

                # Create purchase items + update stock
                for r in resolved_items:
                    PurchaseItem.objects.create(
                        purchase   = purchase,
                        product    = r['product'],
                        quantity   = r['quantity'],
                        unit_cost  = r['unit_cost'],
                        total      = r['total'],
                    )

                    # Update stock
                    stock, _ = InventoryStock.objects.select_for_update().get_or_create(
                        product=r['product'],
                        branch=branch,
                        defaults={'quantity': Decimal('0')},
                    )
                    before = stock.quantity
                    stock.quantity = before + r['quantity']
                    stock.save(update_fields=['quantity', 'last_updated'])

                    # Record inventory transaction
                    InventoryTransaction.objects.create(
                        product          = r['product'],
                        branch           = branch,
                        transaction_type = InventoryTransaction.TYPE_PURCHASE,
                        quantity         = r['quantity'],
                        quantity_before  = before,
                        quantity_after   = stock.quantity,
                        unit_cost        = r['unit_cost'],
                        reference_id     = str(purchase.pk),
                        reference_type   = 'Purchase',
                        notes            = f'Purchase {purchase.purchase_number}',
                        created_by       = request.user,
                    )

                    # Update product cost price to latest
                    r['product'].cost_price = r['unit_cost']
                    r['product'].save(update_fields=['cost_price', 'updated_at'])

                AuditLog.log(
                    action='PURCHASE_CREATED',
                    module='suppliers',
                    user=request.user,
                    object_type='Purchase',
                    object_id=purchase.pk,
                    object_repr=purchase.purchase_number,
                    new_data={
                        'supplier': supplier.name,
                        'total':    str(grand_total),
                        'items':    len(resolved_items),
                    },
                    ip_address=client_ip(request),
                )

            return JsonResponse({
                'success': True,
                'message': f'Purchase {purchase.purchase_number} created.',
                'purchase_id': purchase.pk,
                'purchase_number': purchase.purchase_number,
            })

        except Exception as e:
            logger.exception('Purchase create failed')
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    from apps.branches.models import Branch

    context = {
        'page_title': 'New Purchase',
        'branches':   Branch.objects.filter(status='active'),
        'today':      timezone.now().date(),
    }
    return render(request, 'suppliers/purchase_form.html', context)


# ─── PURCHASE DETAIL ─────────────────────────────────────────

@login_required
def purchase_detail(request, pk):
    if not check_permission(request, PermissionCode.SUPPLIERS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('purchase_list')

    purchase = get_object_or_404(
        Purchase.objects.select_related('supplier', 'branch', 'created_by')
        .prefetch_related('items__product'),
        pk=pk
    )

    context = {
        'page_title':  purchase.purchase_number,
        'purchase':    purchase,
        'items':       purchase.items.all(),
        'can_manage':  check_permission(request, PermissionCode.SUPPLIERS_MANAGE),
    }
    return render(request, 'suppliers/purchase_detail.html', context)


# ─── PAY PURCHASE ────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def purchase_add_payment(request, pk):
    if not check_permission(request, PermissionCode.SUPPLIERS_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    purchase = get_object_or_404(Purchase, pk=pk)

    try:
        amount = Decimal(str(request.POST.get('amount', '0')))
    except (InvalidOperation, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid amount.'}, status=400)

    if amount <= 0:
        return JsonResponse({'success': False, 'error': 'Amount must be positive.'}, status=400)

    if amount > purchase.outstanding:
        return JsonResponse({
            'success': False,
            'error': f'Amount exceeds outstanding balance (Rs. {purchase.outstanding}).',
        }, status=400)

    try:
        with transaction.atomic():
            purchase.amount_paid = purchase.amount_paid + amount
            if purchase.amount_paid >= purchase.total:
                purchase.payment_status = Purchase.PAYMENT_PAID
            else:
                purchase.payment_status = Purchase.PAYMENT_PARTIAL
            purchase.save(update_fields=['amount_paid', 'payment_status', 'updated_at'])

            AuditLog.log(
                action='PURCHASE_PAYMENT',
                module='suppliers',
                user=request.user,
                object_type='Purchase',
                object_id=purchase.pk,
                object_repr=purchase.purchase_number,
                new_data={'amount': str(amount)},
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'Payment of Rs. {amount} recorded.',
        })
    except Exception as e:
        logger.exception('Purchase payment failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)