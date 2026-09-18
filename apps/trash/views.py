"""
AquaFlow — Trash / Recycle Bin
Powered by Quantum Axis

Only Super Admin can restore or permanently delete.
Normal admins cannot access this section.
"""

import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from apps.accounts.models import PermissionCode, RoleCode
from apps.system.models import AuditLog

logger = logging.getLogger('apps')


def is_super_admin(request):
    """Only Super Admin allowed."""
    try:
        return request.user.profile.role.code == RoleCode.SUPER_ADMIN
    except Exception:
        return False


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


# ─── TRASH LIST ──────────────────────────────────────────────

@login_required
def trash_list(request):
    if not is_super_admin(request):
        messages.error(
            request,
            'Only Super Admin can access the Trash. Contact your administrator.'
        )
        return redirect('dashboard')

    from apps.customers.models import Customer
    from apps.vehicles.models import Vehicle
    from apps.services.models import Service
    from apps.inventory.models import Product
    from apps.suppliers.models import Supplier

    item_type = request.GET.get('type', 'all')
    search    = request.GET.get('q', '').strip()

    # Collect all deleted items
    all_items = []

    if item_type in ('all', 'customer'):
        customers = Customer.objects.filter(is_deleted=True).select_related('deleted_by')
        if search:
            customers = customers.filter(
                Q(name__icontains=search) | Q(phone__icontains=search)
            )
        for c in customers:
            all_items.append({
                'type':       'customer',
                'type_label': 'Customer',
                'icon':       'fa-user',
                'color':      'primary',
                'id':         c.pk,
                'name':       c.name,
                'meta':       f'{c.customer_code} · {c.phone or "No phone"}',
                'deleted_at': c.deleted_at,
                'deleted_by': c.deleted_by,
                'restore_url': f'/system/trash/customer/{c.pk}/restore/',
                'delete_url':  f'/system/trash/customer/{c.pk}/purge/',
                'detail_url':  '',
            })

    if item_type in ('all', 'vehicle'):
        vehicles = Vehicle.objects.filter(is_deleted=True).select_related(
            'deleted_by', 'brand', 'model', 'customer'
        )
        if search:
            vehicles = vehicles.filter(
                Q(registration_number__icontains=search) |
                Q(brand__name__icontains=search)
            )
        for v in vehicles:
            all_items.append({
                'type':       'vehicle',
                'type_label': 'Vehicle',
                'icon':       'fa-car',
                'color':      'info',
                'id':         v.pk,
                'name':       v.registration_number,
                'meta':       f'{v.brand.name} {v.model.name} · Owner: {v.customer.name}',
                'deleted_at': v.deleted_at,
                'deleted_by': v.deleted_by,
                'restore_url': f'/system/trash/vehicle/{v.pk}/restore/',
                'delete_url':  f'/system/trash/vehicle/{v.pk}/purge/',
                'detail_url':  '',
            })

    if item_type in ('all', 'service'):
        services = Service.objects.filter(is_deleted=True).select_related('deleted_by', 'category')
        if search:
            services = services.filter(name__icontains=search)
        for s in services:
            all_items.append({
                'type':       'service',
                'type_label': 'Service',
                'icon':       'fa-concierge-bell',
                'color':      'success',
                'id':         s.pk,
                'name':       s.name,
                'meta':       s.category.name if s.category else 'No category',
                'deleted_at': s.deleted_at,
                'deleted_by': s.deleted_by,
                'restore_url': f'/system/trash/service/{s.pk}/restore/',
                'delete_url':  f'/system/trash/service/{s.pk}/purge/',
                'detail_url':  '',
            })

    if item_type in ('all', 'product'):
        products = Product.objects.filter(is_deleted=True).select_related('deleted_by', 'category')
        if search:
            products = products.filter(
                Q(name__icontains=search) | Q(sku__icontains=search)
            )
        for p in products:
            all_items.append({
                'type':       'product',
                'type_label': 'Product',
                'icon':       'fa-box',
                'color':      'warning',
                'id':         p.pk,
                'name':       p.name,
                'meta':       f'SKU: {p.sku} · Rs. {p.selling_price}',
                'deleted_at': p.deleted_at,
                'deleted_by': p.deleted_by,
                'restore_url': f'/system/trash/product/{p.pk}/restore/',
                'delete_url':  f'/system/trash/product/{p.pk}/purge/',
                'detail_url':  '',
            })

    if item_type in ('all', 'supplier'):
        suppliers = Supplier.objects.filter(is_deleted=True).select_related('deleted_by')
        if search:
            suppliers = suppliers.filter(name__icontains=search)
        for s in suppliers:
            all_items.append({
                'type':       'supplier',
                'type_label': 'Supplier',
                'icon':       'fa-truck',
                'color':      'secondary',
                'id':         s.pk,
                'name':       s.name,
                'meta':       s.phone or s.contact_person or 'No contact',
                'deleted_at': s.deleted_at,
                'deleted_by': s.deleted_by,
                'restore_url': f'/system/trash/supplier/{s.pk}/restore/',
                'delete_url':  f'/system/trash/supplier/{s.pk}/purge/',
                'detail_url':  '',
            })

    # Sort by deleted_at descending
    all_items.sort(key=lambda x: x['deleted_at'] or timezone.now(), reverse=True)

    # Count by type
    counts = {
        'customer': Customer.objects.filter(is_deleted=True).count(),
        'vehicle':  Vehicle.objects.filter(is_deleted=True).count(),
        'service':  Service.objects.filter(is_deleted=True).count(),
        'product':  Product.objects.filter(is_deleted=True).count(),
        'supplier': Supplier.objects.filter(is_deleted=True).count(),
    }
    counts['all'] = sum(counts.values())

    paginator = Paginator(all_items, 30)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title': 'Trash',
        'items':      page_obj,
        'page_obj':   page_obj,
        'item_type':  item_type,
        'search':     search,
        'counts':     counts,
        'total':      paginator.count,
    }
    return render(request, 'trash/trash_list.html', context)


# ─── RESTORE ─────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def restore_item(request, item_type, pk):
    if not is_super_admin(request):
        return JsonResponse({
            'success': False,
            'error': 'Only Super Admin can restore items.',
        }, status=403)

    model_map = {
        'customer': ('apps.customers.models', 'Customer'),
        'vehicle':  ('apps.vehicles.models',  'Vehicle'),
        'service':  ('apps.services.models',  'Service'),
        'product':  ('apps.inventory.models', 'Product'),
        'supplier': ('apps.suppliers.models', 'Supplier'),
    }

    if item_type not in model_map:
        return JsonResponse({'success': False, 'error': 'Invalid item type.'}, status=400)

    module_path, class_name = model_map[item_type]
    import importlib
    module = importlib.import_module(module_path)
    Model = getattr(module, class_name)

    try:
        obj = Model.objects.get(pk=pk, is_deleted=True)
    except Model.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found.'}, status=404)

    try:
        with transaction.atomic():
            # Check for conflicts (e.g., duplicate registration number)
            if item_type == 'vehicle':
                from apps.vehicles.models import Vehicle
                if Vehicle.objects.filter(
                    registration_number__iexact=obj.registration_number,
                    is_deleted=False,
                ).exists():
                    return JsonResponse({
                        'success': False,
                        'error': f'Cannot restore. Another vehicle with registration '
                                 f'"{obj.registration_number}" already exists.',
                    }, status=400)

            # Restore
            obj.is_deleted = False
            obj.deleted_at = None
            obj.deleted_by = None
            obj.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

            AuditLog.log(
                action='ITEM_RESTORED',
                module='trash',
                user=request.user,
                object_type=class_name,
                object_id=obj.pk,
                object_repr=str(obj),
                new_data={'type': item_type},
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'{class_name} "{obj}" restored successfully.',
        })
    except Exception as e:
        logger.exception('Restore failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─── PERMANENT DELETE ────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def purge_item(request, item_type, pk):
    """
    Permanently delete an item. Requires:
    - Super Admin
    - Password re-authentication
    - Typed confirmation
    - Dependency check
    """
    if not is_super_admin(request):
        return JsonResponse({
            'success': False,
            'error': 'Only Super Admin can permanently delete items.',
        }, status=403)

    password = request.POST.get('password', '').strip()
    confirm  = request.POST.get('confirm', '').strip()

    if not password:
        return JsonResponse({'success': False, 'error': 'Password required.'}, status=400)

    if confirm != 'DELETE':
        return JsonResponse({
            'success': False,
            'error': 'Type "DELETE" exactly to confirm.',
        }, status=400)

    # Re-authenticate
    user = authenticate(username=request.user.username, password=password)
    if user is None or user.pk != request.user.pk:
        return JsonResponse({'success': False, 'error': 'Invalid password.'}, status=403)

    model_map = {
        'customer': ('apps.customers.models', 'Customer'),
        'vehicle':  ('apps.vehicles.models',  'Vehicle'),
        'service':  ('apps.services.models',  'Service'),
        'product':  ('apps.inventory.models', 'Product'),
        'supplier': ('apps.suppliers.models', 'Supplier'),
    }

    if item_type not in model_map:
        return JsonResponse({'success': False, 'error': 'Invalid item type.'}, status=400)

    module_path, class_name = model_map[item_type]
    import importlib
    module = importlib.import_module(module_path)
    Model = getattr(module, class_name)

    try:
        obj = Model.objects.get(pk=pk, is_deleted=True)
    except Model.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found.'}, status=404)

    # Dependency checks
    dep_check = check_dependencies(item_type, obj)
    if dep_check['has_deps']:
        return JsonResponse({
            'success': False,
            'error': f'Cannot delete. This {item_type} has: {dep_check["message"]}',
        }, status=400)

    obj_name = str(obj)

    try:
        with transaction.atomic():
            AuditLog.log(
                action='ITEM_PURGED',
                module='trash',
                user=request.user,
                object_type=class_name,
                object_id=obj.pk,
                object_repr=obj_name,
                new_data={'type': item_type, 'confirmed_by': request.user.username},
                ip_address=client_ip(request),
            )

            obj.delete()

        return JsonResponse({
            'success': True,
            'message': f'{class_name} "{obj_name}" permanently deleted.',
        })
    except Exception as e:
        logger.exception('Purge failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def check_dependencies(item_type, obj):
    """Check if item has dependent records that block deletion."""
    from django.db.models import ProtectedError

    if item_type == 'customer':
        vehicles = obj.vehicles.count()
        orders   = obj.orders.count() if hasattr(obj, 'orders') else 0
        if orders > 0:
            return {
                'has_deps': True,
                'message': f'{orders} order(s) — cannot delete customers with sales history.',
            }
        if vehicles > 0:
            return {
                'has_deps': True,
                'message': f'{vehicles} vehicle(s). Delete or reassign vehicles first.',
            }

    elif item_type == 'vehicle':
        orders = obj.orders.count() if hasattr(obj, 'orders') else 0
        if orders > 0:
            return {
                'has_deps': True,
                'message': f'{orders} order(s) — cannot delete vehicles with sales history.',
            }

    elif item_type == 'service':
        invoice_items = obj.invoice_items.count() if hasattr(obj, 'invoice_items') else 0
        if invoice_items > 0:
            return {
                'has_deps': True,
                'message': f'{invoice_items} invoice item(s) — cannot delete services with sales history.',
            }

    elif item_type == 'product':
        invoice_items = obj.invoice_items.count() if hasattr(obj, 'invoice_items') else 0
        transactions  = obj.transactions.count() if hasattr(obj, 'transactions') else 0
        if invoice_items > 0:
            return {
                'has_deps': True,
                'message': f'{invoice_items} invoice item(s) with historical sales.',
            }
        if transactions > 0:
            return {
                'has_deps': True,
                'message': f'{transactions} inventory transaction(s) in audit trail.',
            }

    elif item_type == 'supplier':
        purchases = obj.purchases.count() if hasattr(obj, 'purchases') else 0
        if purchases > 0:
            return {
                'has_deps': True,
                'message': f'{purchases} purchase(s) — cannot delete suppliers with history.',
            }

    return {'has_deps': False, 'message': ''}