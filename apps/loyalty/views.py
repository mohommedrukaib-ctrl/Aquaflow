"""
AquaFlow — Loyalty Views
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

from .models import LoyaltyConfig, LoyaltyTransaction
from .services import award_points
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


def award_points(customer, points, tx_type, description='',
                 reference_id='', reference_type='', user=None):
    """
    Award or deduct loyalty points.
    Must be called within a transaction.
    Returns new balance.
    """
    from apps.customers.models import Customer

    if not isinstance(customer, Customer):
        return None

    # Lock customer row
    customer = Customer.objects.select_for_update().get(pk=customer.pk)
    new_balance = customer.loyalty_points + points

    if new_balance < 0:
        return None  # Cannot go negative

    customer.loyalty_points = new_balance
    customer.save(update_fields=['loyalty_points', 'updated_at'])

    LoyaltyTransaction.objects.create(
        customer         = customer,
        transaction_type = tx_type,
        points           = points,
        balance_after    = new_balance,
        reference_id     = reference_id,
        reference_type   = reference_type,
        description      = description,
        created_by       = user,
    )

    return new_balance


# ─── LOYALTY DASHBOARD ───────────────────────────────────────

@login_required
def loyalty_dashboard(request):
    if not check_permission(request, PermissionCode.MEMBERSHIPS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    from apps.customers.models import Customer

    config = LoyaltyConfig.get_config()

    # Top customers by points
    top_customers = Customer.objects.filter(
        is_deleted=False,
        loyalty_points__gt=0,
    ).order_by('-loyalty_points')[:10]

    # Total points issued/redeemed
    total_earned = LoyaltyTransaction.objects.filter(
        transaction_type=LoyaltyTransaction.TYPE_EARN,
    ).aggregate(Sum('points'))['points__sum'] or 0

    total_redeemed = abs(
        LoyaltyTransaction.objects.filter(
            transaction_type=LoyaltyTransaction.TYPE_REDEEM,
        ).aggregate(Sum('points'))['points__sum'] or 0
    )

    total_active = Customer.objects.filter(
        is_deleted=False,
        loyalty_points__gt=0,
    ).count()

    context = {
        'page_title':     'Loyalty Program',
        'config':         config,
        'top_customers':  top_customers,
        'total_earned':   total_earned,
        'total_redeemed': total_redeemed,
        'total_active':   total_active,
        'can_manage':     check_permission(request, PermissionCode.MEMBERSHIPS_MANAGE),
    }
    return render(request, 'loyalty/dashboard.html', context)


@login_required
@require_http_methods(['POST'])
def loyalty_config_update(request):
    if not check_permission(request, PermissionCode.MEMBERSHIPS_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    config = LoyaltyConfig.get_config()

    try:
        config.is_enabled = request.POST.get('is_enabled') == 'true'
        config.points_per_currency = Decimal(request.POST.get('points_per_currency', '1'))
        config.currency_per_point = Decimal(request.POST.get('currency_per_point', '1'))
        config.min_points_to_redeem = int(request.POST.get('min_points_to_redeem', '100'))
        config.max_redemption_percent = Decimal(request.POST.get('max_redemption_percent', '50'))
        config.points_expiry_days = int(request.POST.get('points_expiry_days', '365'))
        config.save()

        return JsonResponse({'success': True, 'message': 'Settings saved.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ─── CUSTOMER LOYALTY HISTORY ────────────────────────────────

@login_required
def customer_loyalty_history(request, customer_id):
    from apps.customers.models import Customer

    customer = get_object_or_404(Customer, pk=customer_id, is_deleted=False)

    transactions = LoyaltyTransaction.objects.filter(
        customer=customer
    ).select_related('created_by').order_by('-created_at')

    paginator = Paginator(transactions, 30)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title':   f'Loyalty History — {customer.name}',
        'customer':     customer,
        'page_obj':     page_obj,
        'transactions': page_obj,
    }
    return render(request, 'loyalty/customer_history.html', context)


# ─── MANUAL POINTS ADJUSTMENT ────────────────────────────────

@login_required
@require_http_methods(['POST'])
def points_adjust(request, customer_id):
    if not check_permission(request, PermissionCode.MEMBERSHIPS_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    from apps.customers.models import Customer

    customer = get_object_or_404(Customer, pk=customer_id, is_deleted=False)

    try:
        points = int(request.POST.get('points', '0'))
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid points.'}, status=400)

    reason = request.POST.get('reason', '').strip()
    if not reason:
        return JsonResponse({'success': False, 'error': 'Reason required.'}, status=400)

    if points == 0:
        return JsonResponse({'success': False, 'error': 'Points cannot be zero.'}, status=400)

    try:
        with transaction.atomic():
            new_balance = award_points(
                customer=customer,
                points=points,
                tx_type=LoyaltyTransaction.TYPE_ADJUST,
                description=reason,
                user=request.user,
            )

            if new_balance is None:
                return JsonResponse({
                    'success': False,
                    'error': 'Would result in negative balance.',
                }, status=400)

            AuditLog.log(
                action='LOYALTY_ADJUSTED',
                module='loyalty',
                user=request.user,
                object_type='Customer',
                object_id=customer.pk,
                object_repr=customer.name,
                new_data={'points': points, 'reason': reason, 'new_balance': new_balance},
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'Points adjusted. New balance: {new_balance}',
            'new_balance': new_balance,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)