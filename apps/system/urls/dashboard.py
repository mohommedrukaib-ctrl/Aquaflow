"""
AquaFlow Dashboard — Modern Edition
Powered by Quantum Axis
"""

from django.urls import path
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta


@login_required
def dashboard(request):
    from apps.customers.models import Customer
    from apps.orders.models import Order
    from apps.bookings.models import Booking
    from apps.payments.models import Payment
    from apps.invoices.models import InvoiceItem
    from apps.vehicles.models import Vehicle

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # ─── TODAY'S STATS ────────────────────────────────────
    try:
        todays_orders = Order.objects.filter(
            created_at__date=today,
            status=Order.STATUS_COMPLETED,
        )
        todays_sales = todays_orders.aggregate(Sum('total'))['total__sum'] or 0
        todays_orders_count = todays_orders.count()
        todays_washes = todays_orders.filter(vehicle__isnull=False).count()
    except Exception:
        todays_sales = 0
        todays_orders_count = 0
        todays_washes = 0

    # ─── YESTERDAY'S SALES (for comparison) ───────────────
    try:
        yesterdays_sales = Order.objects.filter(
            created_at__date=yesterday,
            status=Order.STATUS_COMPLETED,
        ).aggregate(Sum('total'))['total__sum'] or 0
    except Exception:
        yesterdays_sales = 0

    # Calculate percentage change
    if yesterdays_sales > 0:
        sales_change = ((todays_sales - yesterdays_sales) / yesterdays_sales) * 100
    else:
        sales_change = 100 if todays_sales > 0 else 0

    # ─── PENDING BOOKINGS ─────────────────────────────────
    try:
        pending_bookings = Booking.objects.filter(
            status__in=['pending', 'confirmed', 'arrived'],
            scheduled_date__gte=today,
        ).count()

        todays_bookings = Booking.objects.filter(
            scheduled_date=today,
        ).select_related('customer', 'vehicle', 'service').order_by('scheduled_time')[:5]
    except Exception:
        pending_bookings = 0
        todays_bookings = []

    # ─── TOTAL CUSTOMERS ──────────────────────────────────
    try:
        total_customers = Customer.objects.filter(is_deleted=False).count()
        new_customers_week = Customer.objects.filter(
            is_deleted=False,
            created_at__date__gte=week_ago,
        ).count()
    except Exception:
        total_customers = 0
        new_customers_week = 0

    # ─── TOTAL VEHICLES ──────────────────────────────────
    try:
        total_vehicles = Vehicle.objects.filter(is_deleted=False).count()
    except Exception:
        total_vehicles = 0

    # ─── RECENT ORDERS ───────────────────────────────────
    try:
        recent_orders = Order.objects.select_related(
            'customer', 'vehicle'
        ).order_by('-created_at')[:5]
    except Exception:
        recent_orders = []

    # ─── SALES CHART DATA (LAST 7 DAYS) ───────────────────
    sales_chart = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        try:
            day_total = Order.objects.filter(
                created_at__date=day,
                status=Order.STATUS_COMPLETED,
            ).aggregate(Sum('total'))['total__sum'] or 0
        except Exception:
            day_total = 0
        sales_chart.append({
            'date':  day.strftime('%d %b'),
            'day':   day.strftime('%a'),
            'total': float(day_total),
        })

    # ─── TOP SERVICES THIS MONTH ─────────────────────────
    try:
        top_services = InvoiceItem.objects.filter(
            item_type='service',
            invoice__created_at__date__gte=month_ago,
            service__isnull=False,
        ).values(
            'service__name'
        ).annotate(
            count=Count('id'),
            revenue=Sum('line_total'),
        ).order_by('-count')[:5]
    except Exception:
        top_services = []

    # ─── PAYMENT METHODS BREAKDOWN (TODAY) ────────────────
    try:
        payment_breakdown = Payment.objects.filter(
            processed_at__date=today,
            status=Payment.STATUS_COMPLETED,
        ).values(
            'payment_method__name'
        ).annotate(
            total=Sum('amount'),
            count=Count('id'),
        ).order_by('-total')
    except Exception:
        payment_breakdown = []

    context = {
        'page_title': 'Dashboard',
        'stats': {
            'todays_sales':       todays_sales,
            'todays_washes':      todays_washes,
            'todays_orders':      todays_orders_count,
            'pending_bookings':   pending_bookings,
            'total_customers':    total_customers,
            'new_customers_week': new_customers_week,
            'total_vehicles':     total_vehicles,
            'yesterdays_sales':   yesterdays_sales,
            'sales_change':       round(sales_change, 1),
            'sales_up':           sales_change >= 0,
        },
        'recent_orders':     recent_orders,
        'todays_bookings':   todays_bookings,
        'sales_chart':       sales_chart,
        'top_services':      list(top_services),
        'payment_breakdown': list(payment_breakdown),
    }
    return render(request, 'dashboard/dashboard.html', context)


urlpatterns = [
    path('', dashboard, name='dashboard'),
]