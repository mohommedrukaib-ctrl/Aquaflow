"""
AquaFlow — POS Views (Final)
Powered by Quantum Axis

Features:
- Load from Wash Job or Booking
- Cart with editable name/price/qty
- VAT toggle per sale + per item
- Service + Repair + Product + Custom items
- Vehicle auto-reassign when from wash job
- Multiple print formats
"""

import json
import logging
import uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import PermissionCode
from apps.system.models import AuditLog

from django.core.cache import cache
from django.db import IntegrityError

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


@login_required
def pos_home(request):
    if not check_permission(request, PermissionCode.POS_ACCESS):
        messages.error(request, 'You do not have access to POS.')
        return redirect('dashboard')

    from apps.branches.models import Branch
    from apps.payments.models import PaymentMethod
    from apps.businesses.models import Business

    business = Business.objects.get(pk=1)
    branch = None
    if hasattr(request.user, 'profile'):
        branch = request.user.profile.branch
    if not branch:
        branch = Branch.objects.filter(is_default=True).first()

    payment_methods = PaymentMethod.objects.filter(is_active=True).order_by('sort_order', 'name')
    idempotency_key = str(uuid.uuid4())

    prefill = None
    prefill_json = 'null'

    wash_job_id = request.GET.get('wash_job')
    booking_id = request.GET.get('booking')

    if wash_job_id:
        try:
            from apps.wash.models import WashJob
            job = WashJob.objects.select_related(
                'customer', 'vehicle', 'service', 'booking',
            ).prefetch_related('items').get(pk=wash_job_id)

            prefill_items = []
            for item in job.items.all():
                prefill_items.append({
                    'name': item.name, 'type': item.item_type,
                    'unit_price': float(item.unit_price), 'quantity': float(item.quantity),
                    'vat': item.vat_applicable, 'service_id': item.service_id, 'product_id': item.product_id,
                })

            if not prefill_items and job.service:
                price = job.service.get_price_amount(
                    vehicle_type=job.vehicle.vehicle_type if job.vehicle else None, branch=branch,
                )
                prefill_items.append({
                    'name': job.service.name, 'type': 'service', 'unit_price': float(price),
                    'quantity': 1, 'vat': True, 'service_id': job.service.pk, 'product_id': None,
                })

            prefill = {
                'wash_job_id': job.pk, 'job_number': job.job_number, 'booking_id': job.booking_id,
                'customer_id': job.customer.pk, 'customer_name': job.customer.name,
                'vehicle_id': job.vehicle.pk, 'vehicle_reg': job.vehicle.registration_number,
                'items': prefill_items,
            }
            prefill_json = json.dumps(prefill)
        except Exception as e:
            logger.warning(f'Wash job prefill failed: {e}')

    elif booking_id:
        try:
            from apps.bookings.models import Booking
            booking = Booking.objects.select_related('customer', 'vehicle', 'service').get(pk=booking_id)
            price = booking.service.get_price_amount(
                vehicle_type=booking.vehicle.vehicle_type if booking.vehicle else None, branch=branch,
            ) if booking.service else Decimal('0')

            prefill = {
                'wash_job_id': None, 'job_number': None, 'booking_id': booking.pk,
                'customer_id': booking.customer.pk, 'customer_name': booking.customer.name,
                'vehicle_id': booking.vehicle.pk, 'vehicle_reg': booking.vehicle.registration_number,
                'items': [{
                    'name': booking.service.name if booking.service else '', 'type': 'service',
                    'unit_price': float(price), 'quantity': 1, 'vat': True,
                    'service_id': booking.service.pk if booking.service else None, 'product_id': None,
                }] if booking.service else [],
            }
            prefill_json = json.dumps(prefill)
        except Exception as e:
            logger.warning(f'Booking prefill failed: {e}')

    context = {
        'page_title': 'Point of Sale', 'branch': branch, 'business': business,
        'payment_methods': payment_methods, 'idempotency_key': idempotency_key,
        'tax_enabled': business.tax_enabled, 'tax_percentage': float(business.tax_percentage),
        'tax_name': business.tax_name, 'prefill': prefill, 'prefill_json': prefill_json,
    }
    return render(request, 'pos/pos.html', context)


@login_required
def product_search_ajax(request):
    from apps.inventory.models import Product
    q = request.GET.get('q', '').strip()
    show_all = request.GET.get('all', '') == '1'
    products = Product.objects.filter(is_deleted=False, is_active=True)
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    limit = 50 if show_all else 30
    products = products.order_by('name')[:limit]
    data = [{'id': p.pk, 'label': p.name, 'name': p.name, 'sku': p.sku, 'price': str(p.selling_price), 'meta': f'{p.sku} · Rs. {p.selling_price}'} for p in products]
    return JsonResponse({'products': data})


@login_required
def wash_job_search_ajax(request):
    from apps.wash.models import WashJob
    q = request.GET.get('q', '').strip()
    jobs = WashJob.objects.select_related('customer', 'vehicle', 'service', 'branch').filter(
        status__in=[WashJob.STATUS_WAITING, WashJob.STATUS_ASSIGNED, WashJob.STATUS_WASHING, WashJob.STATUS_QUALITY_CHECK, WashJob.STATUS_READY],
    ).exclude(order__isnull=False)
    if q:
        jobs = jobs.filter(Q(job_number__icontains=q) | Q(customer__name__icontains=q) | Q(customer__phone__icontains=q) | Q(vehicle__registration_number__icontains=q))
    jobs = jobs.order_by('-created_at')[:20]
    data = [{'id': j.pk, 'label': f'{j.job_number} — {j.customer.name}', 'meta': f'{j.vehicle.registration_number} · {j.service.name if j.service else "No service"} · {j.get_status_display()}', 'customer_id': j.customer.pk, 'customer_name': j.customer.name, 'vehicle_id': j.vehicle.pk, 'vehicle_reg': j.vehicle.registration_number, 'service_id': j.service.pk if j.service else None, 'service_name': j.service.name if j.service else '', 'job_number': j.job_number, 'status': j.get_status_display()} for j in jobs]
    return JsonResponse({'wash_jobs': data})


@login_required
def booking_search_ajax(request):
    from apps.bookings.models import Booking
    q = request.GET.get('q', '').strip()
    bookings = Booking.objects.select_related('customer', 'vehicle', 'service').exclude(status__in=['completed', 'cancelled'])
    if q:
        bookings = bookings.filter(Q(booking_number__icontains=q) | Q(customer__name__icontains=q) | Q(customer__phone__icontains=q) | Q(vehicle__registration_number__icontains=q))
    else:
        bookings = bookings.filter(scheduled_date__gte=timezone.now().date())
    bookings = bookings.order_by('scheduled_date', 'scheduled_time')[:20]
    data = [{'id': b.pk, 'label': f'{b.booking_number} — {b.customer.name}', 'meta': f'{b.vehicle.registration_number} · {b.service.name} · {b.scheduled_date}', 'customer_id': b.customer.pk, 'customer_name': b.customer.name, 'vehicle_id': b.vehicle.pk, 'vehicle_reg': b.vehicle.registration_number, 'service_id': b.service.pk, 'service_name': b.service.name} for b in bookings]
    return JsonResponse({'bookings': data})


@login_required
def service_price_for_vehicle(request):
    from apps.services.models import Service
    from apps.vehicles.models import Vehicle
    service_id = request.GET.get('service_id')
    vehicle_id = request.GET.get('vehicle_id')
    branch_id = request.GET.get('branch_id')
    try:
        service = Service.objects.get(pk=service_id)
    except Service.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Service not found.'})
    vehicle_type = None
    if vehicle_id:
        v = Vehicle.objects.filter(pk=vehicle_id).first()
        if v:
            vehicle_type = v.vehicle_type
    branch = None
    if branch_id:
        from apps.branches.models import Branch
        branch = Branch.objects.filter(pk=branch_id).first()
    price_amount = service.get_price_amount(vehicle_type=vehicle_type, branch=branch)
    return JsonResponse({'success': True, 'service_id': service.pk, 'service_name': service.name, 'price': str(price_amount), 'has_price': True})


@login_required
@require_http_methods(['POST'])
def product_quick_create(request):
    if not check_permission(request, PermissionCode.INVENTORY_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
    from apps.inventory.models import Product
    name = request.POST.get('name', '').strip()
    selling_price = request.POST.get('selling_price', '0').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'Name required.'}, status=400)
    try:
        price = Decimal(selling_price)
        if price < 0:
            raise ValueError()
    except (InvalidOperation, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid price.'}, status=400)
    existing = Product.objects.filter(name__iexact=name, is_deleted=False).first()
    if existing:
        return JsonResponse({'success': True, 'item': {'id': existing.pk, 'label': existing.name, 'name': existing.name, 'sku': existing.sku, 'price': str(existing.selling_price), 'meta': f'{existing.sku} · Rs. {existing.selling_price}'}, 'message': f'"{name}" exists — selected.'})
    try:
        with transaction.atomic():
            product = Product.objects.create(name=name, selling_price=price, cost_price=Decimal('0'), is_active=True, created_by=request.user)
            AuditLog.log(action='PRODUCT_CREATED', module='pos', user=request.user, object_type='Product', object_id=product.pk, object_repr=product.name, new_data={'name': name, 'price': str(price)}, ip_address=client_ip(request))
        return JsonResponse({'success': True, 'item': {'id': product.pk, 'label': product.name, 'name': product.name, 'sku': product.sku, 'price': str(product.selling_price), 'meta': f'{product.sku} · Rs. {product.selling_price}'}, 'message': f'Product "{product.name}" added.'})
    except Exception as e:
        logger.exception('Product quick create failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def wash_job_items_ajax(request, pk):
    from apps.wash.models import WashJob
    try:
        job = WashJob.objects.select_related('customer', 'vehicle', 'service').prefetch_related('items').get(pk=pk)
    except WashJob.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Job not found.'}, status=404)
    items = []
    for item in job.items.all():
        items.append({'name': item.name, 'type': item.item_type, 'unit_price': float(item.unit_price), 'quantity': float(item.quantity), 'vat': item.vat_applicable, 'service_id': item.service_id, 'product_id': item.product_id})
    if not items and job.service:
        from apps.branches.models import Branch
        branch = Branch.objects.filter(is_default=True).first()
        price = job.service.get_price_amount(vehicle_type=job.vehicle.vehicle_type if job.vehicle else None, branch=branch)
        items.append({'name': job.service.name, 'type': 'service', 'unit_price': float(price), 'quantity': 1, 'vat': True, 'service_id': job.service.pk, 'product_id': None})
    return JsonResponse({'success': True, 'wash_job': {'id': job.pk, 'job_number': job.job_number, 'customer_id': job.customer.pk, 'customer_name': job.customer.name, 'vehicle_id': job.vehicle.pk, 'vehicle_reg': job.vehicle.registration_number, 'booking_id': job.booking_id}, 'items': items})


@login_required
@require_http_methods(['POST'])
def complete_sale(request):
    if not check_permission(request, PermissionCode.POS_ACCESS):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data.'}, status=400)

    idempotency_key = payload.get('idempotency_key')
    if not idempotency_key:
        return JsonResponse({'success': False, 'error': 'Missing idempotency key.'}, status=400)

    cache_key = f'pos_sale:{idempotency_key}'
    if cache.get(cache_key):
        return JsonResponse({'success': False, 'error': 'Duplicate submission ignored.'}, status=400)

    # DB fallback for multi-worker/LocMem safety
    from apps.system.models import SystemSetting
    from django.db import IntegrityError
    try:
        SystemSetting.objects.create(key=cache_key, value='1')
    except IntegrityError:
        return JsonResponse({'success': False, 'error': 'Duplicate submission ignored.'}, status=400)

    cache.set(cache_key, True, timeout=300)

    customer_id = payload.get('customer_id')
    vehicle_id = payload.get('vehicle_id')
    branch_id = payload.get('branch_id')
    wash_job_id = payload.get('wash_job_id')
    booking_id = payload.get('booking_id')
    items = payload.get('items', [])
    payments = payload.get('payments', [])
    notes = payload.get('notes', '')
    vat_enabled = payload.get('vat_enabled', False)

    try:
        order_discount = Decimal(str(payload.get('order_discount', '0')))
    except (InvalidOperation, ValueError):
        order_discount = Decimal('0')

    if not customer_id:
        cache.delete(cache_key)
        return JsonResponse({'success': False, 'error': 'Customer is required.'}, status=400)
    if not branch_id:
        cache.delete(cache_key)
        return JsonResponse({'success': False, 'error': 'Branch is required.'}, status=400)
    if not items:
        cache.delete(cache_key)
        return JsonResponse({'success': False, 'error': 'Cart is empty.'}, status=400)
    if not payments:
        cache.delete(cache_key)
        return JsonResponse({'success': False, 'error': 'Payment is required.'}, status=400)

    from apps.customers.models import Customer
    from apps.vehicles.models import Vehicle
    from apps.services.models import Service
    from apps.inventory.models import Product, InventoryStock, InventoryTransaction
    from apps.branches.models import Branch
    from apps.businesses.models import Business
    from apps.orders.models import Order
    from apps.invoices.models import Invoice, InvoiceItem
    from apps.payments.models import Payment, PaymentMethod
    from apps.bookings.models import Booking
    from apps.wash.models import WashJob, WashBay

    try:
        with transaction.atomic():
            business = Business.objects.get(pk=1)
            branch = Branch.objects.get(pk=branch_id)
            customer = Customer.objects.select_for_update().get(pk=customer_id, is_deleted=False)

            vehicle = None
            if vehicle_id:
                vehicle = Vehicle.objects.get(pk=vehicle_id, is_deleted=False)
                if vehicle.customer_id != customer.pk:
                    if wash_job_id:
                        logger.warning(
                            f'Vehicle {vehicle.registration_number} ownership transferred '
                            f'from {vehicle.customer_id} to {customer.pk} via wash job {wash_job_id}'
                        )
                        vehicle.customer = customer
                        vehicle.save(update_fields=['customer', 'updated_at'])
                    else:
                        raise ValueError(
                            f'Vehicle {vehicle.registration_number} belongs to another customer. '
                            f'Select the correct vehicle or use the wash job flow.'
                        )

            wash_job = None
            if wash_job_id:
                wash_job = WashJob.objects.filter(pk=wash_job_id).first()

            booking = None
            if booking_id:
                booking = Booking.objects.filter(pk=booking_id).first()
            elif wash_job and wash_job.booking:
                booking = wash_job.booking

            if vat_enabled and business.tax_enabled:
                global_tax_pct = business.tax_percentage
            else:
                global_tax_pct = Decimal('0')

            subtotal = Decimal('0')
            tax_total = Decimal('0')
            resolved_items = []
            has_service = False

            for item in items:
                item_name = item.get('name', '').strip()
                item_type = item.get('type', 'service')
                item_vat = item.get('vat', True)

                try:
                    unit_price = Decimal(str(item.get('unit_price', 0)))
                    quantity = Decimal(str(item.get('quantity', 1)))
                    line_disc = Decimal(str(item.get('discount', 0)))
                except (InvalidOperation, ValueError):
                    raise ValueError('Invalid price/quantity.')

                if quantity <= 0:
                    raise ValueError('Quantity must be greater than 0.')
                if unit_price < 0:
                    unit_price = Decimal('0')
                if line_disc < 0:
                    line_disc = Decimal('0')

                description = item_name or 'Unnamed item'

                service_obj = None
                product_obj = None
                service_id = item.get('service_id')
                product_id = item.get('product_id')

                if service_id:
                    try:
                        service_obj = Service.objects.get(pk=service_id)
                    except Service.DoesNotExist:
                        pass

                if product_id:
                    try:
                        product_obj = Product.objects.get(pk=product_id)
                    except Product.DoesNotExist:
                        pass

                if item_type in ('service', 'repair'):
                    has_service = True

                if vat_enabled and item_vat:
                    tax_pct = global_tax_pct
                else:
                    tax_pct = Decimal('0')

                gross = unit_price * quantity
                line_subtotal = gross - line_disc
                if line_subtotal < 0:
                    line_subtotal = Decimal('0')

                line_tax = (line_subtotal * tax_pct / Decimal('100')).quantize(Decimal('0.01'))
                line_total = (line_subtotal + line_tax).quantize(Decimal('0.01'))
                line_subtotal = line_subtotal.quantize(Decimal('0.01'))

                subtotal += line_subtotal
                tax_total += line_tax

                invoice_type = 'service' if item_type in ('service', 'repair', 'custom') else 'product'

                resolved_items.append({
                    'type': invoice_type, 'service': service_obj, 'product': product_obj,
                    'description': description, 'unit_price': unit_price,
                    'quantity': quantity, 'discount': line_disc,
                    'tax': line_tax, 'line_total': line_total,
                })

            if order_discount < 0:
                order_discount = Decimal('0')
            if order_discount > subtotal:
                order_discount = subtotal

            subtotal_after_disc = subtotal - order_discount
            grand_total = (subtotal_after_disc + tax_total).quantize(Decimal('0.01'))

            payment_total = Decimal('0')
            for p in payments:
                try:
                    amt = Decimal(str(p.get('amount', 0)))
                except (InvalidOperation, ValueError):
                    raise ValueError('Invalid payment amount.')
                if amt < 0:
                    raise ValueError('Payment cannot be negative.')
                payment_total += amt

            payment_total = payment_total.quantize(Decimal('0.01'))

            if abs(payment_total - grand_total) > Decimal('0.01'):
                raise ValueError(f'Payment (Rs. {payment_total}) does not match total (Rs. {grand_total}).')

            order = Order.objects.create(
                business=business, branch=branch, customer=customer, vehicle=vehicle,
                booking=booking, subtotal=subtotal, discount_amount=order_discount,
                tax_amount=tax_total, total=grand_total,
                status=Order.STATUS_COMPLETED, payment_status=Order.PAYMENT_PAID,
                notes=notes, created_by=request.user,
            )

            invoice = Invoice.objects.create(
                order=order, subtotal=subtotal, discount_amount=order_discount,
                tax_amount=tax_total, total=grand_total, status=Invoice.STATUS_PAID,
            )

            for r in resolved_items:
                InvoiceItem.objects.create(
                    invoice=invoice, item_type=r['type'],
                    service=r['service'], product=r['product'],
                    description_snapshot=r['description'], unit_price_snapshot=r['unit_price'],
                    quantity=r['quantity'], discount=r['discount'],
                    tax=r['tax'], line_total=r['line_total'],
                )

            for p in payments:
                pm_code = p.get('method_code', '').strip()
                try:
                    pm_amount = Decimal(str(p.get('amount', 0)))
                except (InvalidOperation, ValueError):
                    raise ValueError('Invalid payment amount.')
                if pm_amount <= 0:
                    continue
                method = PaymentMethod.objects.filter(code=pm_code, is_active=True).first()
                if not method:
                    raise ValueError(f'Invalid payment method: {pm_code}')
                Payment.objects.create(
                    invoice=invoice, order=order, payment_method=method,
                    amount=pm_amount, reference=p.get('reference', '').strip(),
                    status=Payment.STATUS_COMPLETED, processed_by=request.user,
                )

            for r in resolved_items:
                if r['type'] == 'product' and r['product']:
                    stock, _ = InventoryStock.objects.select_for_update().get_or_create(
                        product=r['product'], branch=branch, defaults={'quantity': Decimal('0')},
                    )
                    before = stock.quantity
                    stock.quantity = before - r['quantity']
                    stock.save(update_fields=['quantity', 'last_updated'])
                    InventoryTransaction.objects.create(
                        product=r['product'], branch=branch,
                        transaction_type=InventoryTransaction.TYPE_SALE,
                        quantity=-r['quantity'], quantity_before=before,
                        quantity_after=stock.quantity, unit_cost=r['product'].cost_price,
                        reference_id=str(order.pk), reference_type='Order',
                        notes=f'Sale via {order.order_number}', created_by=request.user,
                    )

            if wash_job:
                wash_job.order = order
                wash_job.invoice = invoice
                wash_job.status = WashJob.STATUS_COMPLETED
                wash_job.completed_at = timezone.now()
                wash_job.save(update_fields=['order', 'invoice', 'status', 'completed_at', 'updated_at'])
                if wash_job.wash_bay:
                    wash_job.wash_bay.status = WashBay.STATUS_AVAILABLE
                    wash_job.wash_bay.save(update_fields=['status'])
            elif has_service and vehicle:
                try:
                    first_service = next(
                        (r['service'] for r in resolved_items if r['type'] == 'service' and r['service']),
                        None
                    )
                    if first_service and not WashJob.objects.filter(order=order).exists():
                        WashJob.objects.create(
                            order=order, invoice=invoice, booking=booking,
                            customer=customer, vehicle=vehicle,
                            service=first_service, branch=branch,
                            status=WashJob.STATUS_COMPLETED,
                            completed_at=timezone.now(), created_by=request.user,
                        )
                except Exception as e:
                    logger.warning(f'Auto wash job failed: {e}')

            if booking and booking.status != 'completed':
                booking.status = Booking.STATUS_COMPLETED
                booking.save(update_fields=['status', 'updated_at'])

            try:
                from apps.loyalty.services import award_points
                from apps.loyalty.models import LoyaltyConfig, LoyaltyTransaction
                config = LoyaltyConfig.get_config()
                if config.is_enabled and config.points_per_currency > 0:
                    points = int((grand_total / Decimal('100')) * config.points_per_currency)
                    if points > 0:
                        award_points(customer=customer, points=points, tx_type=LoyaltyTransaction.TYPE_EARN, description=f'Earned from {order.order_number}', reference_id=str(order.pk), reference_type='Order', user=request.user)
            except Exception as e:
                logger.warning(f'Loyalty failed: {e}')

            try:
                if has_service and vehicle:
                    from apps.memberships.models import Membership
                    mem = Membership.objects.filter(customer=customer, status=Membership.STATUS_ACTIVE, expiry_date__gte=timezone.now().date(), wash_count_remaining__gt=0).first()
                    if mem:
                        mem.use_wash(count=1)
            except Exception as e:
                logger.warning(f'Membership failed: {e}')

            AuditLog.log(
                action='ORDER_COMPLETED', module='pos', user=request.user,
                object_type='Order', object_id=order.pk, object_repr=order.order_number,
                new_data={
                    'order_number': order.order_number, 'invoice_number': invoice.invoice_number,
                    'customer': customer.name, 'vehicle': vehicle.registration_number if vehicle else None,
                    'wash_job': wash_job.job_number if wash_job else None,
                    'total': str(grand_total), 'vat_enabled': vat_enabled, 'items_count': len(resolved_items),
                },
                ip_address=client_ip(request),
            )

            logger.info(f'POS Sale: {order.order_number} / {invoice.invoice_number} | Customer: {customer.name} | Total: Rs. {grand_total} | Cashier: {request.user.username}')

    except Customer.DoesNotExist:
        cache.delete(cache_key)
        return JsonResponse({'success': False, 'error': 'Customer not found.'}, status=400)
    except Vehicle.DoesNotExist:
        cache.delete(cache_key)
        return JsonResponse({'success': False, 'error': 'Vehicle not found.'}, status=400)
    except Branch.DoesNotExist:
        cache.delete(cache_key)
        return JsonResponse({'success': False, 'error': 'Branch not found.'}, status=400)
    except Business.DoesNotExist:
        cache.delete(cache_key)
        return JsonResponse({'success': False, 'error': 'Business not configured.'}, status=500)
    except ValueError as e:
        cache.delete(cache_key)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        cache.delete(cache_key)
        logger.exception('Complete sale failed')
        return JsonResponse({'success': False, 'error': f'Sale failed: {str(e)}'}, status=500)

    return JsonResponse({
        'success': True, 'message': 'Sale completed successfully.',
        'order_number': order.order_number, 'invoice_number': invoice.invoice_number,
        'invoice_id': invoice.pk, 'order_id': order.pk, 'total': str(grand_total),
        'receipt_url': f'/pos/receipt/{invoice.pk}/',
    })
@login_required
def receipt_view(request, invoice_id):
    from apps.invoices.models import Invoice
    from apps.businesses.models import Business

    invoice = Invoice.objects.select_related(
        'order', 'order__customer', 'order__vehicle', 'order__branch',
    ).prefetch_related('items', 'payments__payment_method').get(pk=invoice_id)

    business = Business.objects.get(pk=1)
    fmt = request.GET.get('format', business.print_format or 'thermal_80mm')

    template_map = {
        'thermal_80mm': 'pos/receipt_thermal.html',
        'dot_matrix': 'pos/receipt_dotmatrix.html',
        'half_a4': 'pos/receipt_half_a4.html',
        'a4': 'pos/receipt_a4.html',
    }

    template = template_map.get(fmt, 'pos/receipt_thermal.html')

    context = {
        'invoice': invoice, 'order': invoice.order, 'business': business,
        'items': invoice.items.all(), 'payments': invoice.payments.all(),
        'current_format': fmt,
        'formats': [('thermal_80mm', 'Thermal (80mm)'), ('dot_matrix', 'Dot Matrix'), ('half_a4', 'Half A4'), ('a4', 'Full A4')],
    }
    return render(request, template, context)