"""
AquaFlow — Membership Views
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

from .models import MembershipPlan, Membership
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


# ─── PLAN LIST ───────────────────────────────────────────────

@login_required
def plan_list(request):
    if not check_permission(request, PermissionCode.MEMBERSHIPS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    plans = MembershipPlan.objects.all().order_by('sort_order', 'name')

    context = {
        'page_title': 'Membership Plans',
        'plans':      plans,
        'can_manage': check_permission(request, PermissionCode.MEMBERSHIPS_MANAGE),
    }
    return render(request, 'memberships/plan_list.html', context)


@login_required
@require_http_methods(['POST'])
def plan_create_ajax(request):
    if not check_permission(request, PermissionCode.MEMBERSHIPS_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    name          = request.POST.get('name', '').strip()
    price         = request.POST.get('price', '0').strip()
    wash_count    = request.POST.get('wash_count', '0').strip()
    duration_days = request.POST.get('duration_days', '365').strip()
    discount_pct  = request.POST.get('discount_percentage', '0').strip()
    color         = request.POST.get('color', '#04a9f5').strip()

    if not name:
        return JsonResponse({'success': False, 'error': 'Name required.'}, status=400)

    try:
        plan = MembershipPlan.objects.create(
            name=name,
            price=Decimal(price),
            wash_count=int(wash_count),
            duration_days=int(duration_days),
            discount_percentage=Decimal(discount_pct),
            color=color,
            is_active=True,
        )

        AuditLog.log(
            action='MEMBERSHIP_PLAN_CREATED',
            module='memberships',
            user=request.user,
            object_type='MembershipPlan',
            object_id=plan.pk,
            object_repr=plan.name,
            new_data={'name': name, 'price': price, 'wash_count': wash_count},
            ip_address=client_ip(request),
        )

        return JsonResponse({
            'success': True,
            'message': f'Plan "{plan.name}" created.',
        })
    except Exception as e:
        logger.exception('Plan create failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def plan_delete(request, pk):
    if not check_permission(request, PermissionCode.MEMBERSHIPS_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    plan = get_object_or_404(MembershipPlan, pk=pk)

    if plan.memberships.exists():
        return JsonResponse({
            'success': False,
            'error': f'Cannot delete — plan has {plan.memberships.count()} member(s).',
        }, status=400)

    plan.delete()
    return JsonResponse({'success': True, 'message': f'Plan deleted.'})


# ─── MEMBERSHIP LIST ─────────────────────────────────────────

@login_required
def membership_list(request):
    if not check_permission(request, PermissionCode.MEMBERSHIPS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    memberships = Membership.objects.select_related('customer', 'plan')

    if search:
        memberships = memberships.filter(
            Q(membership_number__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(customer__phone__icontains=search)
        )
    if status:
        memberships = memberships.filter(status=status)

    memberships = memberships.order_by('-created_at')

    # Auto-expire memberships
    today = timezone.now().date()
    Membership.objects.filter(
        status=Membership.STATUS_ACTIVE,
        expiry_date__lt=today,
    ).update(status=Membership.STATUS_EXPIRED)

    # Stats
    active_count = Membership.objects.filter(
        status=Membership.STATUS_ACTIVE
    ).count()
    expired_count = Membership.objects.filter(
        status=Membership.STATUS_EXPIRED
    ).count()

    paginator = Paginator(memberships, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title':    'Memberships',
        'page_obj':      page_obj,
        'memberships':   page_obj,
        'search':        search,
        'status':        status,
        'total_count':   paginator.count,
        'active_count':  active_count,
        'expired_count': expired_count,
        'status_choices': Membership.STATUS_CHOICES,
        'plans':         MembershipPlan.objects.filter(is_active=True),
        'can_manage':    check_permission(request, PermissionCode.MEMBERSHIPS_MANAGE),
    }
    return render(request, 'memberships/membership_list.html', context)


@login_required
@require_http_methods(['POST'])
def membership_create_ajax(request):
    if not check_permission(request, PermissionCode.MEMBERSHIPS_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    from apps.customers.models import Customer

    customer_id = request.POST.get('customer_id')
    plan_id     = request.POST.get('plan_id')
    start_date  = request.POST.get('start_date', '')
    amount_paid = request.POST.get('amount_paid', '0').strip()
    notes       = request.POST.get('notes', '').strip()

    if not customer_id or not plan_id:
        return JsonResponse({
            'success': False,
            'error': 'Customer and plan required.',
        }, status=400)

    try:
        with transaction.atomic():
            customer = Customer.objects.get(pk=customer_id, is_deleted=False)
            plan     = MembershipPlan.objects.get(pk=plan_id, is_active=True)

            if not start_date:
                start_date = timezone.now().date()

            membership = Membership.objects.create(
                customer   = customer,
                plan       = plan,
                start_date = start_date,
                amount_paid= Decimal(amount_paid or '0'),
                notes      = notes,
                status     = Membership.STATUS_ACTIVE,
                created_by = request.user,
            )

            AuditLog.log(
                action='MEMBERSHIP_CREATED',
                module='memberships',
                user=request.user,
                object_type='Membership',
                object_id=membership.pk,
                object_repr=membership.membership_number,
                new_data={
                    'customer':   customer.name,
                    'plan':       plan.name,
                    'washes':     plan.wash_count,
                    'expires':    str(membership.expiry_date),
                },
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'Membership {membership.membership_number} created.',
            'membership_number': membership.membership_number,
        })
    except Exception as e:
        logger.exception('Membership create failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def membership_detail(request, pk):
    if not check_permission(request, PermissionCode.MEMBERSHIPS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('membership_list')

    membership = get_object_or_404(
        Membership.objects.select_related('customer', 'plan'),
        pk=pk
    )

    context = {
        'page_title':  membership.membership_number,
        'membership':  membership,
        'can_manage':  check_permission(request, PermissionCode.MEMBERSHIPS_MANAGE),
    }
    return render(request, 'memberships/membership_detail.html', context)