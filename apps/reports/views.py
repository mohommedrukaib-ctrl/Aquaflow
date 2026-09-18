"""
AquaFlow — Reports Views
Powered by Quantum Axis
"""

import csv
import logging
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q, F
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.accounts.models import PermissionCode

logger = logging.getLogger('apps')


def check_permission(request, code):
    try:
        return request.user.profile.has_permission(code)
    except Exception:
        return False


def parse_date_range(request):
    """Parse date_from and date_to from request, default to last 30 days."""
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')

    today = timezone.now().date()

    if not date_from:
        date_from = (today - timedelta(days=30)).isoformat()
    if not date_to:
        date_to = today.isoformat()

    return date_from, date_to


# ─── REPORTS HOME ────────────────────────────────────────────

@login_required
def reports_home(request):
    if not check_permission(request, PermissionCode.REPORTS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    return render(request, 'reports/home.html', {
        'page_title': 'Reports',
    })


# ─── SALES REPORT ────────────────────────────────────────────

@login_required
def sales_report(request):
    if not check_permission(request, PermissionCode.REPORTS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    from apps.orders.models import Order
    from django.db.models.functions import TruncDate, TruncMonth

    date_from, date_to = parse_date_range(request)
    group_by = request.GET.get('group', 'day')  # day/month

    orders = Order.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        status=Order.STATUS_COMPLETED,
    )

    # Total stats
    total_sales   = orders.aggregate(Sum('total'))['total__sum'] or 0
    total_orders  = orders.count()
    total_tax     = orders.aggregate(Sum('tax_amount'))['tax_amount__sum'] or 0
    total_discount = orders.aggregate(Sum('discount_amount'))['discount_amount__sum'] or 0
    avg_order     = orders.aggregate(Avg('total'))['total__avg'] or 0

    # Group by day or month
    if group_by == 'month':
        trend = orders.annotate(
            period=TruncMonth('created_at')
        ).values('period').annotate(
            total=Sum('total'),
            count=Count('id'),
        ).order_by('period')
    else:
        trend = orders.annotate(
            period=TruncDate('created_at')
        ).values('period').annotate(
            total=Sum('total'),
            count=Count('id'),
        ).order_by('period')

    trend_list = list(trend)
    max_val = max([float(t['total']) for t in trend_list], default=1)

    # Handle CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{date_from}_to_{date_to}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Period', 'Orders', 'Total'])
        for row in trend_list:
            writer.writerow([
                row['period'].strftime('%Y-%m-%d' if group_by == 'day' else '%Y-%m'),
                row['count'],
                str(row['total']),
            ])
        return response

    context = {
        'page_title':     'Sales Report',
        'date_from':      date_from,
        'date_to':        date_to,
        'group_by':       group_by,
        'total_sales':    total_sales,
        'total_orders':   total_orders,
        'total_tax':      total_tax,
        'total_discount': total_discount,
        'avg_order':      avg_order,
        'trend':          trend_list,
        'max_val':        max_val,
    }
    return render(request, 'reports/sales.html', context)


# ─── SERVICE POPULARITY REPORT ───────────────────────────────

@login_required
def service_report(request):
    if not check_permission(request, PermissionCode.REPORTS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    from apps.invoices.models import InvoiceItem

    date_from, date_to = parse_date_range(request)

    services = InvoiceItem.objects.filter(
        item_type='service',
        service__isnull=False,
        invoice__created_at__date__gte=date_from,
        invoice__created_at__date__lte=date_to,
    ).values(
        'service__name', 'service__category__name'
    ).annotate(
        count=Count('id'),
        quantity=Sum('quantity'),
        revenue=Sum('line_total'),
    ).order_by('-revenue')

    services_list = list(services)
    total_revenue = sum([float(s['revenue']) for s in services_list])

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="service_report_{date_from}_to_{date_to}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Service', 'Category', 'Count', 'Quantity', 'Revenue'])
        for row in services_list:
            writer.writerow([
                row['service__name'],
                row['service__category__name'] or '',
                row['count'],
                row['quantity'],
                str(row['revenue']),
            ])
        return response

    context = {
        'page_title':    'Service Report',
        'date_from':     date_from,
        'date_to':       date_to,
        'services':      services_list,
        'total_revenue': total_revenue,
    }
    return render(request, 'reports/services.html', context)


# ─── CUSTOMER REPORT ─────────────────────────────────────────

@login_required
def customer_report(request):
    if not check_permission(request, PermissionCode.REPORTS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    from apps.customers.models import Customer

    date_from, date_to = parse_date_range(request)

    customers = Customer.objects.filter(
        is_deleted=False,
    ).annotate(
        order_count=Count(
            'orders',
            filter=Q(
                orders__status='completed',
                orders__created_at__date__gte=date_from,
                orders__created_at__date__lte=date_to,
            )
        ),
        total_spent=Sum(
            'orders__total',
            filter=Q(
                orders__status='completed',
                orders__created_at__date__gte=date_from,
                orders__created_at__date__lte=date_to,
            )
        ),
    ).filter(order_count__gt=0).order_by('-total_spent')[:100]

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="customer_report_{date_from}_to_{date_to}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Customer', 'Phone', 'Orders', 'Total Spent'])
        for c in customers:
            writer.writerow([
                c.name, c.phone, c.order_count, str(c.total_spent or 0),
            ])
        return response

    context = {
        'page_title': 'Customer Report',
        'date_from':  date_from,
        'date_to':    date_to,
        'customers':  customers,
    }
    return render(request, 'reports/customers.html', context)


# ─── VEHICLE REPORT ──────────────────────────────────────────

@login_required
def vehicle_report(request):
    if not check_permission(request, PermissionCode.REPORTS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    from apps.vehicles.models import Vehicle

    date_from, date_to = parse_date_range(request)

    vehicles = Vehicle.objects.filter(
        is_deleted=False,
    ).select_related('customer', 'brand', 'model').annotate(
        wash_count=Count(
            'orders',
            filter=Q(
                orders__status='completed',
                orders__created_at__date__gte=date_from,
                orders__created_at__date__lte=date_to,
            )
        ),
        total_spent=Sum(
            'orders__total',
            filter=Q(
                orders__status='completed',
                orders__created_at__date__gte=date_from,
                orders__created_at__date__lte=date_to,
            )
        ),
    ).filter(wash_count__gt=0).order_by('-wash_count')[:100]

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="vehicle_report_{date_from}_to_{date_to}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Registration', 'Vehicle', 'Owner', 'Wash Count', 'Total Spent'])
        for v in vehicles:
            writer.writerow([
                v.registration_number,
                f'{v.brand.name} {v.model.name}',
                v.customer.name,
                v.wash_count,
                str(v.total_spent or 0),
            ])
        return response

    context = {
        'page_title': 'Vehicle Report',
        'date_from':  date_from,
        'date_to':    date_to,
        'vehicles':   vehicles,
    }
    return render(request, 'reports/vehicles.html', context)


# ─── CASHIER PERFORMANCE ─────────────────────────────────────

@login_required
def cashier_report(request):
    if not check_permission(request, PermissionCode.REPORTS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    from apps.orders.models import Order

    date_from, date_to = parse_date_range(request)

    cashiers = Order.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        status=Order.STATUS_COMPLETED,
    ).exclude(created_by__isnull=True).values(
        'created_by__username',
        'created_by__first_name',
        'created_by__last_name',
    ).annotate(
        order_count=Count('id'),
        total_sales=Sum('total'),
        avg_order=Avg('total'),
    ).order_by('-total_sales')

    cashiers_list = list(cashiers)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="cashier_report_{date_from}_to_{date_to}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Cashier', 'Orders', 'Total Sales', 'Avg Order'])
        for c in cashiers_list:
            name = c.get('created_by__username', '')
            writer.writerow([
                name, c['order_count'],
                str(c['total_sales']), str(c['avg_order']),
            ])
        return response

    context = {
        'page_title': 'Cashier Report',
        'date_from':  date_from,
        'date_to':    date_to,
        'cashiers':   cashiers_list,
    }
    return render(request, 'reports/cashiers.html', context)


# ─── PAYMENT METHOD BREAKDOWN ────────────────────────────────

@login_required
def payment_report(request):
    if not check_permission(request, PermissionCode.REPORTS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    from apps.payments.models import Payment

    date_from, date_to = parse_date_range(request)

    payments = Payment.objects.filter(
        processed_at__date__gte=date_from,
        processed_at__date__lte=date_to,
        status=Payment.STATUS_COMPLETED,
    ).values(
        'payment_method__name',
    ).annotate(
        count=Count('id'),
        total=Sum('amount'),
    ).order_by('-total')

    payments_list = list(payments)
    grand_total = sum([float(p['total']) for p in payments_list])

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="payment_report_{date_from}_to_{date_to}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Method', 'Transactions', 'Total'])
        for p in payments_list:
            writer.writerow([
                p['payment_method__name'], p['count'], str(p['total']),
            ])
        writer.writerow(['GRAND TOTAL', '', str(grand_total)])
        return response

    context = {
        'page_title':  'Payment Report',
        'date_from':   date_from,
        'date_to':     date_to,
        'payments':    payments_list,
        'grand_total': grand_total,
    }
    return render(request, 'reports/payments.html', context)


# ─── INVENTORY REPORT ────────────────────────────────────────

@login_required
def inventory_report(request):
    if not check_permission(request, PermissionCode.REPORTS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    from apps.inventory.models import Product

    filter_type = request.GET.get('filter', 'all')  # all, low, out

    products = Product.objects.filter(
        is_deleted=False
    ).select_related('category', 'unit').prefetch_related('stock_entries')

    products_with_stock = []
    total_value = Decimal('0')
    low_count = 0
    out_count = 0

    for p in products:
        stock = p.get_stock()
        stock_value = stock * p.cost_price
        total_value += stock_value

        is_low = p.reorder_level > 0 and stock <= p.reorder_level
        is_out = stock <= 0

        if is_out:
            out_count += 1
        elif is_low:
            low_count += 1

        # Apply filter
        if filter_type == 'low' and not is_low:
            continue
        if filter_type == 'out' and not is_out:
            continue

        products_with_stock.append({
            'product': p,
            'stock':   stock,
            'value':   stock_value,
            'is_low':  is_low,
            'is_out':  is_out,
        })

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="inventory_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['SKU', 'Product', 'Category', 'Stock', 'Cost', 'Selling', 'Value', 'Status'])
        for row in products_with_stock:
            p = row['product']
            status = 'OUT' if row['is_out'] else ('LOW' if row['is_low'] else 'OK')
            writer.writerow([
                p.sku, p.name,
                p.category.name if p.category else '',
                row['stock'], str(p.cost_price), str(p.selling_price),
                str(row['value']), status,
            ])
        return response

    context = {
        'page_title':  'Inventory Report',
        'products':    products_with_stock,
        'total_value': total_value,
        'low_count':   low_count,
        'out_count':   out_count,
        'filter_type': filter_type,
    }
    return render(request, 'reports/inventory.html', context)


# ─── PROFIT & LOSS ───────────────────────────────────────────

@login_required
def profit_loss_report(request):
    if not check_permission(request, PermissionCode.REPORTS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    from apps.orders.models import Order
    from apps.finance.models import Expense
    from apps.suppliers.models import Purchase

    date_from, date_to = parse_date_range(request)

    # Revenue
    revenue = Order.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        status=Order.STATUS_COMPLETED,
    ).aggregate(Sum('total'))['total__sum'] or 0

    tax_collected = Order.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        status=Order.STATUS_COMPLETED,
    ).aggregate(Sum('tax_amount'))['tax_amount__sum'] or 0

    # Expenses
    total_expenses = Expense.objects.filter(
        expense_date__gte=date_from,
        expense_date__lte=date_to,
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # Expenses by category
    expenses_by_cat = Expense.objects.filter(
        expense_date__gte=date_from,
        expense_date__lte=date_to,
    ).values('category__name').annotate(
        total=Sum('amount'),
        count=Count('id'),
    ).order_by('-total')

    # Purchases (inventory bought)
    total_purchases = Purchase.objects.filter(
        purchase_date__gte=date_from,
        purchase_date__lte=date_to,
    ).aggregate(Sum('total'))['total__sum'] or 0

    # Gross revenue = order totals - tax (tax is not income)
    gross_revenue = revenue - tax_collected

    # Net profit = revenue - expenses - purchases (simplified)
    net_profit = gross_revenue - total_expenses - total_purchases

    context = {
        'page_title':      'Profit & Loss',
        'date_from':       date_from,
        'date_to':         date_to,
        'revenue':         revenue,
        'gross_revenue':   gross_revenue,
        'tax_collected':   tax_collected,
        'total_expenses':  total_expenses,
        'total_purchases': total_purchases,
        'net_profit':      net_profit,
        'expenses_by_cat': list(expenses_by_cat),
    }
    return render(request, 'reports/profit_loss.html', context) 