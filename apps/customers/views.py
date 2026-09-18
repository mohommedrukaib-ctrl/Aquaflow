"""
AquaFlow — Customer Views
Powered by Quantum Axis

All permission checks are backend-enforced.
Never trust frontend.
"""

import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q

from .models import Customer
from .forms import CustomerForm
from apps.system.models import AuditLog
from apps.accounts.models import PermissionCode

logger = logging.getLogger('apps')


# ─── Permission Helper ────────────────────────────────────────

def check_permission(request, permission_code):
    """
    Backend permission check.
    Returns True if user has permission.
    Never rely on frontend hiding of buttons.
    """
    try:
        return request.user.profile.has_permission(permission_code)
    except Exception:
        return False


def permission_denied(request, message='Permission denied.'):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': message}, status=403)
    messages.error(request, message)
    return redirect('customer_list')


# ─── Customer List ────────────────────────────────────────────

@login_required
def customer_list(request):
    """
    Paginated, searchable customer list.
    Excludes soft-deleted records by default.
    """
    if not check_permission(request, PermissionCode.CUSTOMERS_VIEW):
        messages.error(request, 'You do not have permission to view customers.')
        return redirect('dashboard')

    # ─── Search ───────────────────────────────────────────────
    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', 'active')

    customers = Customer.objects.filter(
        is_deleted=False
    ).select_related('branch')

    if status and status != 'all':
        customers = customers.filter(status=status)

    if search:
        customers = customers.filter(
            Q(name__icontains=search)   |
            Q(phone__icontains=search)  |
            Q(email__icontains=search)  |
            Q(customer_code__icontains=search)
        )

    customers = customers.order_by('-created_at')

    # ─── Pagination ───────────────────────────────────────────
    paginator = Paginator(customers, 25)
    page      = request.GET.get('page', 1)
    page_obj  = paginator.get_page(page)

    context = {
        'page_title':  'Customers',
        'page_obj':    page_obj,
        'customers':   page_obj,
        'search':      search,
        'status':      status,
        'total_count': paginator.count,
        'can_create':  check_permission(request, PermissionCode.CUSTOMERS_CREATE),
        'can_edit':    check_permission(request, PermissionCode.CUSTOMERS_EDIT),
        'can_delete':  check_permission(request, PermissionCode.CUSTOMERS_DELETE),
        'breadcrumbs': [
            {'label': 'Customers', 'url': None}
        ],
    }
    return render(request, 'customers/customer_list.html', context)


# ─── Customer Detail ──────────────────────────────────────────

@login_required
def customer_detail(request, pk):
    if not check_permission(request, PermissionCode.CUSTOMERS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    customer = get_object_or_404(
        Customer,
        pk=pk,
        is_deleted=False
    )

    vehicles = customer.vehicles.filter(
        is_deleted=False
    ).select_related(
        'brand', 'model', 'vehicle_type', 'color'
    ) if hasattr(customer, 'vehicles') else []

    context = {
        'page_title': f'{customer.name}',
        'customer':   customer,
        'vehicles':   vehicles,
        'can_edit':   check_permission(
            request, PermissionCode.CUSTOMERS_EDIT
        ),
        'can_delete': check_permission(
            request, PermissionCode.CUSTOMERS_DELETE
        ),
        'breadcrumbs': [
            {'label': 'Customers', 'url': '/customers/'},
            {'label': customer.name, 'url': None},
        ],
    }
    return render(request, 'customers/customer_detail.html', context)


# ─── Customer Create ──────────────────────────────────────────

@login_required
@require_http_methods(['GET', 'POST'])
def customer_create(request):
    if not check_permission(request, PermissionCode.CUSTOMERS_CREATE):
        return permission_denied(request, 'You cannot create customers.')

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    customer = form.save(commit=False)
                    customer.created_by = request.user

                    # Assign default business
                    from apps.businesses.models import Business
                    customer.business = Business.objects.get(pk=1)

                    # Assign default branch
                    from apps.branches.models import Branch
                    branch = Branch.objects.filter(
                        is_default=True
                    ).first()
                    if branch:
                        customer.branch = branch

                    customer.save()

                    # ─── Audit Log ────────────────────────────
                    AuditLog.log(
                        action      = 'CUSTOMER_CREATED',
                        module      = 'customers',
                        user        = request.user,
                        object_type = 'Customer',
                        object_id   = customer.pk,
                        object_repr = str(customer),
                        new_data    = {
                            'name':          customer.name,
                            'phone':         customer.phone,
                            'email':         customer.email,
                            'customer_code': customer.customer_code,
                        },
                        ip_address  = get_client_ip(request),
                    )

                    logger.info(
                        f'Customer created: {customer.customer_code} '
                        f'by {request.user.username}'
                    )

                    if is_ajax:
                        return JsonResponse({
                            'success':  True,
                            'message':  f'Customer {customer.name} created successfully.',
                            'customer': {
                                'id':            customer.pk,
                                'name':          customer.name,
                                'customer_code': customer.customer_code,
                                'phone':         customer.phone,
                                'email':         customer.email,
                            }
                        })

                    messages.success(
                        request,
                        f'✓ Customer {customer.name} '
                        f'({customer.customer_code}) created successfully.'
                    )
                    return redirect('customer_detail', pk=customer.pk)

            except Exception as e:
                logger.error(f'Customer create error: {e}')
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'error':   'Failed to create customer. Please try again.'
                    }, status=500)
                messages.error(request, 'Failed to create customer.')
        else:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'errors':  form.errors,
                }, status=400)
    else:
        form = CustomerForm()

    if is_ajax:
        # Return form HTML for modal
        return render(
            request,
            'customers/partials/customer_form_modal.html',
            {'form': form}
        )

    context = {
        'page_title': 'Add Customer',
        'form':       form,
        'action':     'Create',
        'breadcrumbs': [
            {'label': 'Customers', 'url': '/customers/'},
            {'label': 'Add Customer', 'url': None},
        ],
    }
    return render(request, 'customers/customer_form.html', context)


# ─── Customer Edit ────────────────────────────────────────────

@login_required
@require_http_methods(['GET', 'POST'])
def customer_edit(request, pk):
    if not check_permission(request, PermissionCode.CUSTOMERS_EDIT):
        return permission_denied(request, 'You cannot edit customers.')

    customer = get_object_or_404(Customer, pk=pk, is_deleted=False)
    previous_data = {
        'name':   customer.name,
        'phone':  customer.phone,
        'email':  customer.email,
        'status': customer.status,
    }

    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            try:
                with transaction.atomic():
                    customer = form.save()

                    # ─── Audit Log ────────────────────────────
                    AuditLog.log(
                        action        = 'CUSTOMER_UPDATED',
                        module        = 'customers',
                        user          = request.user,
                        object_type   = 'Customer',
                        object_id     = customer.pk,
                        object_repr   = str(customer),
                        previous_data = previous_data,
                        new_data      = {
                            'name':   customer.name,
                            'phone':  customer.phone,
                            'email':  customer.email,
                            'status': customer.status,
                        },
                        ip_address = get_client_ip(request),
                    )

                    messages.success(
                        request,
                        f'✓ Customer {customer.name} updated successfully.'
                    )
                    return redirect('customer_detail', pk=customer.pk)

            except Exception as e:
                logger.error(f'Customer edit error: {e}')
                messages.error(request, 'Failed to update customer.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomerForm(instance=customer)

    context = {
        'page_title': f'Edit — {customer.name}',
        'form':       form,
        'customer':   customer,
        'action':     'Update',
        'breadcrumbs': [
            {'label': 'Customers',    'url': '/customers/'},
            {'label': customer.name,  'url': f'/customers/{pk}/'},
            {'label': 'Edit',         'url': None},
        ],
    }
    return render(request, 'customers/customer_form.html', context)


# ─── Customer Delete (Soft) ───────────────────────────────────

@login_required
@require_http_methods(['POST'])
def customer_delete(request, pk):
    if not check_permission(request, PermissionCode.CUSTOMERS_DELETE):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'},
            status=403
        )

    customer = get_object_or_404(Customer, pk=pk, is_deleted=False)

    try:
        with transaction.atomic():
            customer_name = customer.name
            customer_code = customer.customer_code
            customer.soft_delete(user=request.user)

            AuditLog.log(
                action      = 'CUSTOMER_DELETED',
                module      = 'customers',
                user        = request.user,
                object_type = 'Customer',
                object_id   = customer.pk,
                object_repr = f'{customer_name} ({customer_code})',
                ip_address  = get_client_ip(request),
            )

            logger.info(
                f'Customer soft-deleted: {customer_code} '
                f'by {request.user.username}'
            )

        return JsonResponse({
            'success': True,
            'message': f'Customer {customer_name} moved to Trash.',
        })

    except Exception as e:
        logger.error(f'Customer delete error: {e}')
        return JsonResponse(
            {'success': False, 'error': 'Failed to delete customer.'},
            status=500
        )


# ─── AJAX Customer Search (for POS) ──────────────────────────

@login_required
def customer_search_ajax(request):
    q = request.GET.get('q', '').strip()
    show_all = request.GET.get('all', '') == '1'

    customers = Customer.objects.filter(
        is_deleted=False,
        status=Customer.STATUS_ACTIVE,
    )

    if q:
        customers = customers.filter(
            Q(name__icontains=q) |
            Q(phone__icontains=q) |
            Q(customer_code__icontains=q)
        )

    limit = 30 if show_all else 15
    customers = customers.order_by('name')[:limit]

    data = [
        {
            'id':            c.pk,
            'label':         c.name,
            'name':          c.name,
            'phone':         c.phone,
            'customer_code': c.customer_code,
            'meta':          f'{c.customer_code} · {c.phone}' if c.phone else c.customer_code,
        }
        for c in customers
    ]
    return JsonResponse({'customers': data})
# ─── Helper ───────────────────────────────────────────────────

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ─── AJAX Phone Lookup ────────────────────────────────────────

@login_required
def customer_phone_lookup(request):
    """
    Lookup customer by phone number (exact prefix match).
    Used when adding a customer — suggests existing match.
    """
    phone = request.GET.get('phone', '').strip()

    if len(phone) < 3:
        return JsonResponse({'match': None})

    customer = Customer.objects.filter(
        is_deleted=False,
        phone__startswith=phone,
    ).first()

    if customer:
        return JsonResponse({
            'match': {
                'id':            customer.pk,
                'name':          customer.name,
                'phone':         customer.phone,
                'customer_code': customer.customer_code,
            }
        })
    return JsonResponse({'match': None})

