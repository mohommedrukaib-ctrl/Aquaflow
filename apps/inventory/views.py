"""
AquaFlow — Inventory Views
Powered by Quantum Axis
"""

import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import (
    Product, ProductCategory, Unit,
    InventoryStock, InventoryTransaction,
)
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


def get_default_branch():
    from apps.branches.models import Branch
    return Branch.objects.filter(is_default=True).first()


def record_stock_transaction(product, branch, quantity, tx_type,
                              user, unit_cost=None,
                              reference_id='', reference_type='',
                              notes=''):
    """
    Record a stock movement AND update InventoryStock.
    Called from ANY place that changes stock.
    Must be called within a transaction.
    """
    stock, _ = InventoryStock.objects.select_for_update().get_or_create(
        product=product,
        branch=branch,
        defaults={'quantity': Decimal('0')},
    )

    before = stock.quantity
    stock.quantity = before + Decimal(str(quantity))
    stock.save(update_fields=['quantity', 'last_updated'])

    if unit_cost is None:
        unit_cost = product.cost_price

    InventoryTransaction.objects.create(
        product          = product,
        branch           = branch,
        transaction_type = tx_type,
        quantity         = Decimal(str(quantity)),
        quantity_before  = before,
        quantity_after   = stock.quantity,
        unit_cost        = unit_cost,
        reference_id     = reference_id,
        reference_type   = reference_type,
        notes            = notes,
        created_by       = user,
    )

    return stock


# ─── PRODUCT LIST ────────────────────────────────────────────

@login_required
def product_list(request):
    if not check_permission(request, PermissionCode.INVENTORY_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    search      = request.GET.get('q', '').strip()
    category    = request.GET.get('category', '')
    stock_filter = request.GET.get('stock', '')

    products = Product.objects.filter(
        is_deleted=False
    ).select_related('category', 'unit').prefetch_related('stock_entries')

    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(sku__icontains=search) |
            Q(barcode__icontains=search) |
            Q(category__name__icontains=search)
        )
    if category:
        products = products.filter(category_id=category)

    products = products.order_by('name')

    # For low stock filter
    if stock_filter == 'low':
        low_stock_ids = []
        for p in products:
            if p.reorder_level > 0 and p.get_stock() <= p.reorder_level:
                low_stock_ids.append(p.pk)
        products = products.filter(pk__in=low_stock_ids)

    paginator = Paginator(products, 30)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    # Attach stock info to each product
    branch = get_default_branch()
    for p in page_obj:
        p.current_stock = p.get_stock(branch=branch) if branch else p.get_stock()
        p.is_low = p.reorder_level > 0 and p.current_stock <= p.reorder_level

    total_products = Product.objects.filter(is_deleted=False).count()
    low_stock_count = 0
    for p in Product.objects.filter(is_deleted=False, is_active=True):
        if p.reorder_level > 0 and p.get_stock() <= p.reorder_level:
            low_stock_count += 1

    context = {
        'page_title':     'Inventory',
        'page_obj':       page_obj,
        'products':       page_obj,
        'search':         search,
        'category':       category,
        'stock_filter':   stock_filter,
        'total_count':    paginator.count,
        'total_products': total_products,
        'low_stock_count': low_stock_count,
        'categories':     ProductCategory.objects.filter(is_active=True),
        'can_manage':     check_permission(request, PermissionCode.INVENTORY_MANAGE),
    }
    return render(request, 'inventory/product_list.html', context)


# ─── PRODUCT DETAIL (with stock history) ─────────────────────

@login_required
def product_detail(request, pk):
    if not check_permission(request, PermissionCode.INVENTORY_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('product_list')

    product = get_object_or_404(
        Product.objects.select_related('category', 'unit'),
        pk=pk, is_deleted=False
    )

    # Stock per branch
    stock_by_branch = InventoryStock.objects.filter(
        product=product
    ).select_related('branch')

    # Recent transactions
    transactions = InventoryTransaction.objects.filter(
        product=product
    ).select_related('branch', 'created_by').order_by('-created_at')[:50]

    total_stock = product.get_stock()

    context = {
        'page_title':      product.name,
        'product':         product,
        'stock_by_branch': stock_by_branch,
        'transactions':    transactions,
        'total_stock':     total_stock,
        'is_low':          product.is_low_stock,
        'can_manage':      check_permission(request, PermissionCode.INVENTORY_MANAGE),
    }
    return render(request, 'inventory/product_detail.html', context)


# ─── STOCK ADJUSTMENT ────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def stock_adjust(request, pk):
    """Manually adjust stock (breakage, count correction, etc.)"""
    if not check_permission(request, PermissionCode.INVENTORY_MANAGE):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'}, status=403
        )

    product = get_object_or_404(Product, pk=pk, is_deleted=False)

    try:
        quantity = Decimal(str(request.POST.get('quantity', '0')))
    except (InvalidOperation, ValueError):
        return JsonResponse(
            {'success': False, 'error': 'Invalid quantity.'}, status=400
        )

    adjustment_type = request.POST.get('type', 'set')  # 'set' | 'add' | 'subtract'
    reason = request.POST.get('reason', '').strip()
    branch_id = request.POST.get('branch_id')

    if not reason:
        return JsonResponse(
            {'success': False, 'error': 'Reason required.'}, status=400
        )

    from apps.branches.models import Branch
    branch = None
    if branch_id:
        branch = Branch.objects.filter(pk=branch_id).first()
    if not branch:
        branch = get_default_branch()
    if not branch:
        return JsonResponse(
            {'success': False, 'error': 'No branch available.'}, status=400
        )

    try:
        with transaction.atomic():
            current = product.get_stock(branch=branch)

            if adjustment_type == 'set':
                # Set to specific value
                diff = quantity - current
            elif adjustment_type == 'add':
                diff = quantity
            elif adjustment_type == 'subtract':
                diff = -quantity
            else:
                return JsonResponse(
                    {'success': False, 'error': 'Invalid adjustment type.'},
                    status=400
                )

            record_stock_transaction(
                product=product,
                branch=branch,
                quantity=diff,
                tx_type=InventoryTransaction.TYPE_ADJUSTMENT,
                user=request.user,
                notes=reason,
            )

            AuditLog.log(
                action='STOCK_ADJUSTED',
                module='inventory',
                user=request.user,
                object_type='Product',
                object_id=product.pk,
                object_repr=product.name,
                new_data={
                    'branch':          branch.name,
                    'before':          str(current),
                    'change':          str(diff),
                    'after':           str(current + diff),
                    'reason':          reason,
                    'type':            adjustment_type,
                },
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'Stock adjusted successfully.',
            'new_stock': str(current + diff),
        })
    except Exception as e:
        logger.exception('Stock adjust failed')
        return JsonResponse(
            {'success': False, 'error': str(e)}, status=500
        )


# ─── STOCK IN (Receive Inventory) ────────────────────────────

@login_required
@require_http_methods(['POST'])
def stock_in(request, pk):
    """Receive stock (e.g., from purchase)."""
    if not check_permission(request, PermissionCode.INVENTORY_MANAGE):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'}, status=403
        )

    product = get_object_or_404(Product, pk=pk, is_deleted=False)

    try:
        quantity = Decimal(str(request.POST.get('quantity', '0')))
        unit_cost = Decimal(str(request.POST.get('unit_cost', '0')))
    except (InvalidOperation, ValueError):
        return JsonResponse(
            {'success': False, 'error': 'Invalid values.'}, status=400
        )

    if quantity <= 0:
        return JsonResponse(
            {'success': False, 'error': 'Quantity must be positive.'},
            status=400
        )

    reason    = request.POST.get('reason', 'Stock received').strip()
    branch_id = request.POST.get('branch_id')

    from apps.branches.models import Branch
    branch = None
    if branch_id:
        branch = Branch.objects.filter(pk=branch_id).first()
    if not branch:
        branch = get_default_branch()

    try:
        with transaction.atomic():
            record_stock_transaction(
                product=product,
                branch=branch,
                quantity=quantity,
                tx_type=InventoryTransaction.TYPE_PURCHASE,
                user=request.user,
                unit_cost=unit_cost if unit_cost > 0 else product.cost_price,
                notes=reason,
            )

            # Update product cost price if new cost provided
            if unit_cost > 0:
                product.cost_price = unit_cost
                product.save(update_fields=['cost_price', 'updated_at'])

            AuditLog.log(
                action='STOCK_RECEIVED',
                module='inventory',
                user=request.user,
                object_type='Product',
                object_id=product.pk,
                object_repr=product.name,
                new_data={
                    'branch':    branch.name,
                    'quantity':  str(quantity),
                    'unit_cost': str(unit_cost),
                    'notes':     reason,
                },
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'Received {quantity} units.',
            'new_stock': str(product.get_stock(branch=branch)),
        })
    except Exception as e:
        logger.exception('Stock in failed')
        return JsonResponse(
            {'success': False, 'error': str(e)}, status=500
        )


# ─── ADD PRODUCT (AJAX) ──────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def product_create_ajax(request):
    if not check_permission(request, PermissionCode.INVENTORY_MANAGE):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'}, status=403
        )

    name          = request.POST.get('name', '').strip()
    selling_price = request.POST.get('selling_price', '').strip()
    cost_price    = request.POST.get('cost_price', '0').strip()
    reorder_level = request.POST.get('reorder_level', '0').strip()
    category_id   = request.POST.get('category_id', '')
    unit_id       = request.POST.get('unit_id', '')
    initial_stock = request.POST.get('initial_stock', '0').strip()

    if not name:
        return JsonResponse(
            {'success': False, 'error': 'Name required.'}, status=400
        )

    try:
        selling = Decimal(selling_price or '0')
        cost    = Decimal(cost_price or '0')
        reorder = Decimal(reorder_level or '0')
        initial = Decimal(initial_stock or '0')
    except (InvalidOperation, ValueError):
        return JsonResponse(
            {'success': False, 'error': 'Invalid numeric values.'}, status=400
        )

    if selling < 0 or cost < 0:
        return JsonResponse(
            {'success': False, 'error': 'Prices must be positive.'}, status=400
        )

    try:
        with transaction.atomic():
            category = None
            if category_id:
                category = ProductCategory.objects.filter(pk=category_id).first()

            unit = None
            if unit_id:
                unit = Unit.objects.filter(pk=unit_id).first()

            # Check duplicate
            existing = Product.objects.filter(
                name__iexact=name, is_deleted=False
            ).first()
            if existing:
                return JsonResponse({
                    'success': False,
                    'error':   f'Product "{name}" already exists.',
                }, status=400)

            product = Product.objects.create(
                name=name,
                selling_price=selling,
                cost_price=cost,
                reorder_level=reorder,
                category=category,
                unit=unit,
                is_active=True,
                created_by=request.user,
            )

            # Add initial stock if provided
            if initial > 0:
                branch = get_default_branch()
                if branch:
                    record_stock_transaction(
                        product=product,
                        branch=branch,
                        quantity=initial,
                        tx_type=InventoryTransaction.TYPE_INITIAL,
                        user=request.user,
                        notes='Initial stock on product creation',
                    )

            AuditLog.log(
                action='PRODUCT_CREATED',
                module='inventory',
                user=request.user,
                object_type='Product',
                object_id=product.pk,
                object_repr=product.name,
                new_data={
                    'name':          product.name,
                    'selling_price': str(selling),
                    'cost_price':    str(cost),
                    'initial_stock': str(initial),
                },
                ip_address=client_ip(request),
            )

            return JsonResponse({
                'success': True,
                'item': {
                    'id':    product.pk,
                    'label': product.name,
                    'name':  product.name,
                    'sku':   product.sku,
                    'price': str(product.selling_price),
                    'meta':  f'{product.sku} · Rs. {product.selling_price}',
                },
                'message': f'Product "{product.name}" added.',
            })
    except Exception as e:
        logger.exception('Product create failed')
        return JsonResponse(
            {'success': False, 'error': f'Failed: {e}'}, status=500
        )


# ─── INLINE EDIT ─────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def product_inline_edit(request, pk):
    if not check_permission(request, PermissionCode.INVENTORY_MANAGE):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'}, status=403
        )

    product = get_object_or_404(Product, pk=pk, is_deleted=False)

    field = request.POST.get('field', '').strip()
    value = request.POST.get('value', '').strip()

    if field not in ['name', 'selling_price', 'cost_price', 'reorder_level']:
        return JsonResponse(
            {'success': False, 'error': 'Invalid field.'}, status=400
        )

    previous = {field: str(getattr(product, field))}

    if field == 'name':
        if len(value) < 2:
            return JsonResponse(
                {'success': False, 'error': 'Name too short.'}, status=400
            )
        if Product.objects.filter(
            name__iexact=value, is_deleted=False
        ).exclude(pk=product.pk).exists():
            return JsonResponse({
                'success': False,
                'error':   f'Another product named "{value}" exists.',
            }, status=400)
        product.name = value
    else:
        try:
            amount = Decimal(value)
            if amount < 0:
                raise ValueError('Negative')
        except (InvalidOperation, ValueError):
            return JsonResponse(
                {'success': False, 'error': 'Invalid value.'}, status=400
            )
        setattr(product, field, amount)

    product.save(update_fields=[field, 'updated_at'])

    AuditLog.log(
        action='PRODUCT_UPDATED',
        module='inventory',
        user=request.user,
        object_type='Product',
        object_id=product.pk,
        object_repr=product.name,
        previous_data=previous,
        new_data={field: str(getattr(product, field))},
        ip_address=client_ip(request),
    )

    return JsonResponse({
        'success': True,
        'message': 'Updated.',
        'value':   str(getattr(product, field)),
    })


# ─── DELETE PRODUCT (soft) ───────────────────────────────────

@login_required
@require_http_methods(['POST'])
def product_delete(request, pk):
    if not check_permission(request, PermissionCode.INVENTORY_MANAGE):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'}, status=403
        )

    product = get_object_or_404(Product, pk=pk, is_deleted=False)

    product.is_deleted = True
    product.deleted_at = timezone.now()
    product.deleted_by = request.user
    product.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    AuditLog.log(
        action='PRODUCT_DELETED',
        module='inventory',
        user=request.user,
        object_type='Product',
        object_id=product.pk,
        object_repr=product.name,
        ip_address=client_ip(request),
    )

    return JsonResponse({
        'success': True,
        'message': f'Product "{product.name}" moved to trash.',
    })


# ─── STOCK MOVEMENTS (Global) ────────────────────────────────

@login_required
def stock_movements(request):
    if not check_permission(request, PermissionCode.INVENTORY_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('product_list')

    search    = request.GET.get('q', '').strip()
    tx_type   = request.GET.get('type', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')

    transactions = InventoryTransaction.objects.select_related(
        'product', 'branch', 'created_by'
    )

    if search:
        transactions = transactions.filter(
            Q(product__name__icontains=search) |
            Q(product__sku__icontains=search) |
            Q(notes__icontains=search)
        )
    if tx_type:
        transactions = transactions.filter(transaction_type=tx_type)
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)

    transactions = transactions.order_by('-created_at')

    paginator = Paginator(transactions, 50)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title':   'Stock Movements',
        'page_obj':     page_obj,
        'transactions': page_obj,
        'search':       search,
        'tx_type':      tx_type,
        'date_from':    date_from,
        'date_to':      date_to,
        'total_count':  paginator.count,
        'type_choices': InventoryTransaction.TYPE_CHOICES,
    }
    return render(request, 'inventory/stock_movements.html', context)