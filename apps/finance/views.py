"""
AquaFlow — Finance / Expense Views
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
from datetime import timedelta

from .models import Expense, ExpenseCategory
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


# ─── EXPENSE LIST ────────────────────────────────────────────

@login_required
def expense_list(request):
    if not check_permission(request, PermissionCode.FINANCE_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    search     = request.GET.get('q', '').strip()
    category   = request.GET.get('category', '')
    date_from  = request.GET.get('date_from', '')
    date_to    = request.GET.get('date_to', '')

    expenses = Expense.objects.select_related(
        'category', 'branch', 'payment_method', 'created_by',
    )

    if search:
        expenses = expenses.filter(
            Q(expense_number__icontains=search) |
            Q(description__icontains=search) |
            Q(notes__icontains=search)
        )
    if category:
        expenses = expenses.filter(category_id=category)
    if date_from:
        expenses = expenses.filter(expense_date__gte=date_from)
    if date_to:
        expenses = expenses.filter(expense_date__lte=date_to)

    expenses = expenses.order_by('-expense_date', '-created_at')

    total_amount = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    total_count  = expenses.count()

    # Monthly summary (this month)
    today = timezone.now().date()
    month_start = today.replace(day=1)
    monthly_total = Expense.objects.filter(
        expense_date__gte=month_start,
        expense_date__lte=today,
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # By category (this month)
    by_category = Expense.objects.filter(
        expense_date__gte=month_start,
    ).values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id'),
    ).order_by('-total')[:5]

    paginator = Paginator(expenses, 30)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title':    'Expenses',
        'page_obj':      page_obj,
        'expenses':      page_obj,
        'search':        search,
        'category':      category,
        'date_from':     date_from,
        'date_to':       date_to,
        'total_amount':  total_amount,
        'total_count':   total_count,
        'monthly_total': monthly_total,
        'by_category':   list(by_category),
        'categories':    ExpenseCategory.objects.filter(is_active=True),
        'can_manage':    check_permission(request, PermissionCode.FINANCE_MANAGE),
    }
    return render(request, 'finance/expense_list.html', context)


# ─── EXPENSE CREATE ──────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def expense_create_ajax(request):
    if not check_permission(request, PermissionCode.FINANCE_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    from apps.branches.models import Branch
    from apps.businesses.models import Business
    from apps.payments.models import PaymentMethod

    try:
        amount = Decimal(str(request.POST.get('amount', '0')))
    except (InvalidOperation, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid amount.'}, status=400)

    if amount <= 0:
        return JsonResponse({'success': False, 'error': 'Amount must be positive.'}, status=400)

    description   = request.POST.get('description', '').strip()
    category_id   = request.POST.get('category_id', '')
    expense_date  = request.POST.get('expense_date', '')
    payment_id    = request.POST.get('payment_method_id', '')
    notes         = request.POST.get('notes', '').strip()

    if not description:
        return JsonResponse({'success': False, 'error': 'Description required.'}, status=400)
    if not category_id:
        return JsonResponse({'success': False, 'error': 'Category required.'}, status=400)
    if not expense_date:
        expense_date = timezone.now().date()

    try:
        with transaction.atomic():
            category = ExpenseCategory.objects.get(pk=category_id)
            branch   = None
            if hasattr(request.user, 'profile'):
                branch = request.user.profile.branch
            if not branch:
                branch = Branch.objects.filter(is_default=True).first()

            business = Business.objects.get(pk=1)

            payment_method = None
            if payment_id:
                payment_method = PaymentMethod.objects.filter(pk=payment_id).first()

            expense = Expense.objects.create(
                category       = category,
                branch         = branch,
                business       = business,
                amount         = amount,
                description    = description,
                expense_date   = expense_date,
                payment_method = payment_method,
                notes          = notes,
                status         = Expense.STATUS_APPROVED,
                approved_by    = request.user,
                approved_at    = timezone.now(),
                created_by     = request.user,
            )

            AuditLog.log(
                action='EXPENSE_CREATED',
                module='finance',
                user=request.user,
                object_type='Expense',
                object_id=expense.pk,
                object_repr=expense.expense_number,
                new_data={
                    'amount':      str(amount),
                    'category':    category.name,
                    'description': description,
                },
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'Expense {expense.expense_number} recorded.',
            'expense_number': expense.expense_number,
        })
    except Exception as e:
        logger.exception('Expense create failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─── EXPENSE DELETE ──────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def expense_delete(request, pk):
    if not check_permission(request, PermissionCode.FINANCE_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    expense = get_object_or_404(Expense, pk=pk)
    number = expense.expense_number

    AuditLog.log(
        action='EXPENSE_DELETED',
        module='finance',
        user=request.user,
        object_type='Expense',
        object_id=expense.pk,
        object_repr=number,
        previous_data={
            'amount':      str(expense.amount),
            'description': expense.description,
        },
        ip_address=client_ip(request),
    )

    expense.delete()

    return JsonResponse({
        'success': True,
        'message': f'Expense {number} deleted.',
    })


# ─── AJAX: Category Search ───────────────────────────────────

@login_required
def category_search_ajax(request):
    q = request.GET.get('q', '').strip()
    show_all = request.GET.get('all', '') == '1'

    cats = ExpenseCategory.objects.filter(is_active=True)
    if q:
        cats = cats.filter(name__icontains=q)

    limit = 30 if show_all else 20
    cats = cats.order_by('sort_order', 'name')[:limit]

    data = [{'id': c.pk, 'label': c.name, 'name': c.name} for c in cats]
    return JsonResponse({'categories': data})


@login_required
@require_http_methods(['POST'])
def category_create_ajax(request):
    if not check_permission(request, PermissionCode.FINANCE_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'Name required.'}, status=400)

    existing = ExpenseCategory.objects.filter(name__iexact=name).first()
    if existing:
        return JsonResponse({
            'success': True,
            'item': {'id': existing.pk, 'label': existing.name, 'name': existing.name},
            'message': f'"{name}" already exists.',
        })

    cat = ExpenseCategory.objects.create(name=name, is_active=True)
    return JsonResponse({
        'success': True,
        'item': {'id': cat.pk, 'label': cat.name, 'name': cat.name},
        'message': f'Category "{cat.name}" added.',
    })