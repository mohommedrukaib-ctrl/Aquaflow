"""
AquaFlow — Employee Views
Powered by Quantum Axis
"""

import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta

from .models import Employee, EmployeePosition
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


# ─── EMPLOYEE LIST ───────────────────────────────────────────

@login_required
def employee_list(request):
    if not check_permission(request, PermissionCode.EMPLOYEES_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', 'active')

    employees = Employee.objects.filter(
        is_deleted=False
    ).select_related('position', 'branch', 'user')

    if status and status != 'all':
        employees = employees.filter(status=status)

    if search:
        employees = employees.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(phone__icontains=search) |
            Q(employee_code__icontains=search) |
            Q(email__icontains=search)
        )

    employees = employees.order_by('first_name', 'last_name')

    paginator = Paginator(employees, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    positions = EmployeePosition.objects.filter(is_active=True).order_by('name')

    from apps.branches.models import Branch
    branches = Branch.objects.filter(status='active')

    context = {
        'page_title':  'Employees',
        'page_obj':    page_obj,
        'employees':   page_obj,
        'search':      search,
        'status':      status,
        'total_count': paginator.count,
        'positions':   positions,
        'branches':    branches,
        'can_manage':  check_permission(request, PermissionCode.EMPLOYEES_MANAGE),
    }
    return render(request, 'employees/employee_list.html', context)


# ─── EMPLOYEE CREATE ─────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def employee_create(request):
    if not check_permission(request, PermissionCode.EMPLOYEES_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    first_name = request.POST.get('first_name', '').strip()
    last_name  = request.POST.get('last_name', '').strip()
    phone      = request.POST.get('phone', '').strip()
    email      = request.POST.get('email', '').strip()
    position_id = request.POST.get('position_id', '')
    branch_id  = request.POST.get('branch_id', '')
    hire_date  = request.POST.get('hire_date', '')
    salary     = request.POST.get('salary', '0').strip()
    commission = request.POST.get('commission_rate', '0').strip()
    nic_number = request.POST.get('nic_number', '').strip()
    notes      = request.POST.get('notes', '').strip()

    if not first_name:
        return JsonResponse({'success': False, 'error': 'First name required.'}, status=400)

    try:
        salary_dec = Decimal(salary or '0')
        commission_dec = Decimal(commission or '0')
    except (InvalidOperation, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid salary/commission.'}, status=400)

    try:
        with transaction.atomic():
            from apps.branches.models import Branch
            from apps.businesses.models import Business

            branch = None
            if branch_id:
                branch = Branch.objects.filter(pk=branch_id).first()
            if not branch:
                branch = Branch.objects.filter(is_default=True).first()

            position = None
            if position_id:
                position = EmployeePosition.objects.filter(pk=position_id).first()

            employee = Employee.objects.create(
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email,
                position=position,
                branch=branch,
                business=Business.objects.get(pk=1),
                hire_date=hire_date or None,
                salary=salary_dec,
                commission_rate=commission_dec,
                nic_number=nic_number,
                notes=notes,
                status=Employee.STATUS_ACTIVE,
                created_by=request.user,
            )

            AuditLog.log(
                action='EMPLOYEE_CREATED',
                module='employees',
                user=request.user,
                object_type='Employee',
                object_id=employee.pk,
                object_repr=str(employee),
                new_data={
                    'name': employee.full_name,
                    'code': employee.employee_code,
                    'position': position.name if position else None,
                },
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'Employee {employee.full_name} ({employee.employee_code}) added.',
        })
    except Exception as e:
        logger.exception('Employee create failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─── EMPLOYEE DETAIL ─────────────────────────────────────────

@login_required
def employee_detail(request, pk):
    if not check_permission(request, PermissionCode.EMPLOYEES_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('employee_list')

    employee = get_object_or_404(
        Employee.objects.select_related('position', 'branch', 'user'),
        pk=pk, is_deleted=False,
    )

    # Performance stats (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)

    try:
        from apps.wash.models import WashJob
        wash_count = WashJob.objects.filter(
            assigned_employee=employee.user,
            created_at__gte=thirty_days_ago,
            status='completed',
        ).count() if employee.user else 0
    except Exception:
        wash_count = 0

    try:
        from apps.orders.models import Order
        sales = Order.objects.filter(
            created_by=employee.user,
            created_at__gte=thirty_days_ago,
            status='completed',
        ).aggregate(
            count=Count('id'),
            total=Sum('total'),
        ) if employee.user else {'count': 0, 'total': 0}
    except Exception:
        sales = {'count': 0, 'total': 0}

    context = {
        'page_title':  employee.full_name,
        'employee':    employee,
        'wash_count':  wash_count,
        'sales':       sales,
        'can_manage':  check_permission(request, PermissionCode.EMPLOYEES_MANAGE),
    }
    return render(request, 'employees/employee_detail.html', context)


# ─── EMPLOYEE INLINE EDIT ────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def employee_inline_edit(request, pk):
    if not check_permission(request, PermissionCode.EMPLOYEES_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    employee = get_object_or_404(Employee, pk=pk, is_deleted=False)

    field = request.POST.get('field', '').strip()
    value = request.POST.get('value', '').strip()

    allowed = ['first_name', 'last_name', 'phone', 'email', 'salary', 'commission_rate', 'nic_number', 'status']

    if field not in allowed:
        return JsonResponse({'success': False, 'error': 'Invalid field.'}, status=400)

    previous = {field: str(getattr(employee, field))}

    if field in ['salary', 'commission_rate']:
        try:
            value = Decimal(value)
        except (InvalidOperation, ValueError):
            return JsonResponse({'success': False, 'error': 'Invalid number.'}, status=400)

    setattr(employee, field, value)
    employee.save(update_fields=[field, 'updated_at'])

    AuditLog.log(
        action='EMPLOYEE_UPDATED',
        module='employees',
        user=request.user,
        object_type='Employee',
        object_id=employee.pk,
        object_repr=str(employee),
        previous_data=previous,
        new_data={field: str(getattr(employee, field))},
        ip_address=client_ip(request),
    )

    return JsonResponse({'success': True, 'message': 'Updated.', 'value': str(getattr(employee, field))})


# ─── EMPLOYEE DELETE (soft) ──────────────────────────────────

@login_required
@require_http_methods(['POST'])
def employee_delete(request, pk):
    if not check_permission(request, PermissionCode.EMPLOYEES_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    employee = get_object_or_404(Employee, pk=pk, is_deleted=False)
    name = employee.full_name

    employee.soft_delete(user=request.user)

    AuditLog.log(
        action='EMPLOYEE_DELETED',
        module='employees',
        user=request.user,
        object_type='Employee',
        object_id=employee.pk,
        object_repr=name,
        ip_address=client_ip(request),
    )

    return JsonResponse({
        'success': True,
        'message': f'Employee {name} moved to trash.',
    })


# ─── AJAX: Employee Search ───────────────────────────────────

@login_required
def employee_search_ajax(request):
    q = request.GET.get('q', '').strip()
    show_all = request.GET.get('all', '') == '1'

    employees = Employee.objects.filter(
        is_deleted=False, status=Employee.STATUS_ACTIVE,
    )

    if q:
        employees = employees.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(phone__icontains=q) |
            Q(employee_code__icontains=q)
        )

    limit = 30 if show_all else 15
    employees = employees.select_related('position').order_by('first_name')[:limit]

    data = [
        {
            'id':    e.pk,
            'label': e.full_name,
            'name':  e.full_name,
            'code':  e.employee_code,
            'meta':  f'{e.employee_code} · {e.position.name if e.position else "No position"}',
        }
        for e in employees
    ]
    return JsonResponse({'employees': data})


# ─── POSITION MANAGEMENT ─────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def position_create_ajax(request):
    if not check_permission(request, PermissionCode.EMPLOYEES_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'Name required.'}, status=400)

    existing = EmployeePosition.objects.filter(name__iexact=name).first()
    if existing:
        return JsonResponse({
            'success': True,
            'item': {'id': existing.pk, 'label': existing.name, 'name': existing.name},
            'message': f'"{name}" already exists.',
        })

    pos = EmployeePosition.objects.create(name=name, is_active=True)
    return JsonResponse({
        'success': True,
        'item': {'id': pos.pk, 'label': pos.name, 'name': pos.name},
        'message': f'Position "{pos.name}" added.',
    })


@login_required
def position_search_ajax(request):
    q = request.GET.get('q', '').strip()
    positions = EmployeePosition.objects.filter(is_active=True)
    if q:
        positions = positions.filter(name__icontains=q)
    positions = positions.order_by('name')[:20]
    data = [{'id': p.pk, 'label': p.name, 'name': p.name} for p in positions]
    return JsonResponse({'positions': data})