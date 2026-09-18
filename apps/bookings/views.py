"""
AquaFlow — Booking Views
Powered by Quantum Axis
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import BookingForm
from .models import Booking
from apps.accounts.models import PermissionCode
from apps.system.models import AuditLog

logger = logging.getLogger('apps')


def check_permission(request, permission):
    try:
        return request.user.profile.has_permission(permission)
    except Exception:
        return False


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ─── BOOKING LIST ─────────────────────────────────────────────

@login_required
def booking_list(request):
    if not check_permission(request, PermissionCode.BOOKINGS_VIEW):
        messages.error(request, 'You do not have permission to view bookings.')
        return redirect('dashboard')

    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    date = request.GET.get('date', '')

    bookings = Booking.objects.select_related(
        'customer',
        'vehicle',
        'vehicle__brand',
        'vehicle__model',
        'service',
        'branch',
        'wash_bay',
        'assigned_employee',
    )

    if query:
        bookings = bookings.filter(
            Q(booking_number__icontains=query)
            | Q(customer__name__icontains=query)
            | Q(customer__phone__icontains=query)
            | Q(vehicle__registration_number__icontains=query)
        )

    if status:
        bookings = bookings.filter(status=status)

    if date:
        bookings = bookings.filter(scheduled_date=date)

    paginator = Paginator(bookings, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title': 'Bookings',
        'page_obj': page_obj,
        'bookings': page_obj,
        'query': query,
        'status': status,
        'date': date,
        'status_choices': Booking.STATUS_CHOICES,
        'can_manage': check_permission(
            request,
            PermissionCode.BOOKINGS_MANAGE,
        ),
    }

    return render(request, 'bookings/booking_list.html', context)


# ─── BOOKING CREATE ───────────────────────────────────────────

@login_required
@require_http_methods(['GET', 'POST'])
def booking_create(request):
    if not check_permission(request, PermissionCode.BOOKINGS_MANAGE):
        messages.error(request, 'Permission denied.')
        return redirect('booking_list')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                post_data = _resolve_booking_pending(request)

                # ─── Set default status to PENDING on Add ─────
                if not post_data.get('status'):
                    post_data['status'] = Booking.STATUS_PENDING

                form = BookingForm(post_data)

                if form.is_valid():
                    booking = form.save(commit=False)
                    booking.business_id = 1
                    booking.created_by = request.user
                    if not booking.duration_minutes:
                        booking.duration_minutes = booking.service.duration_minutes
                    booking.full_clean()
                    booking.save()

                    AuditLog.log(
                        action='BOOKING_CREATED',
                        module='bookings',
                        user=request.user,
                        object_type='Booking',
                        object_id=booking.pk,
                        object_repr=str(booking),
                        new_data={
                            'booking_number': booking.booking_number,
                            'customer':       booking.customer.name,
                            'vehicle':        booking.vehicle.registration_number,
                            'service':        booking.service.name,
                            'date':           str(booking.scheduled_date),
                            'time':           str(booking.scheduled_time),
                        },
                        ip_address=client_ip(request),
                    )

                    messages.success(
                        request,
                        f'Booking {booking.booking_number} created successfully.',
                    )
                    return redirect('booking_detail', pk=booking.pk)
                else:
                    messages.error(request, 'Please fix the errors below.')
                    logger.warning(f'Booking form errors: {form.errors}')
        except Exception as e:
            logger.exception('Booking creation failed')
            messages.error(request, f'Booking could not be created: {e}')
            form = BookingForm(request.POST)
    else:
        form = BookingForm()

    return render(request, 'bookings/booking_form.html', {
        'page_title': 'Add Booking',
        'form': form,
        'action': 'Create',
    })


# ─── BOOKING DETAIL ───────────────────────────────────────────

@login_required
def booking_detail(request, pk):
    if not check_permission(request, PermissionCode.BOOKINGS_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    booking = get_object_or_404(
        Booking.objects.select_related(
            'customer',
            'vehicle',
            'vehicle__brand',
            'vehicle__model',
            'service',
            'branch',
            'wash_bay',
            'assigned_employee',
        ),
        pk=pk,
    )

    return render(request, 'bookings/booking_detail.html', {
        'page_title': booking.booking_number,
        'booking': booking,
        'can_manage': check_permission(
            request,
            PermissionCode.BOOKINGS_MANAGE,
        ),
    })


# ─── BOOKING EDIT ─────────────────────────────────────────────

@login_required
@require_http_methods(['GET', 'POST'])
def booking_edit(request, pk):
    if not check_permission(request, PermissionCode.BOOKINGS_MANAGE):
        messages.error(request, 'Permission denied.')
        return redirect('booking_list')

    booking = get_object_or_404(Booking, pk=pk)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                post_data = _resolve_booking_pending(request)
                form = BookingForm(post_data, instance=booking)
                if form.is_valid():
                    booking = form.save(commit=False)
                    booking.full_clean()
                    booking.save()

                    AuditLog.log(
                        action='BOOKING_UPDATED',
                        module='bookings',
                        user=request.user,
                        object_type='Booking',
                        object_id=booking.pk,
                        object_repr=str(booking),
                        new_data={
                            'status': booking.status,
                            'date':   str(booking.scheduled_date),
                            'time':   str(booking.scheduled_time),
                        },
                        ip_address=client_ip(request),
                    )

                    messages.success(request, 'Booking updated successfully.')
                    return redirect('booking_detail', pk=booking.pk)
                else:
                    messages.error(request, 'Please fix the errors below.')
        except Exception as e:
            logger.exception('Booking update failed')
            messages.error(request, f'Booking could not be updated: {e}')
    else:
        form = BookingForm(instance=booking)

    return render(request, 'bookings/booking_form.html', {
        'page_title': f'Edit {booking.booking_number}',
        'form':       form,
        'booking':    booking,
        'action':     'Update',
    })


# ─── BOOKING STATUS UPDATE ────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def booking_status_update(request, pk):
    if not check_permission(request, PermissionCode.BOOKINGS_MANAGE):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'},
            status=403,
        )

    booking = get_object_or_404(Booking, pk=pk)
    new_status = request.POST.get('status', '').strip()

    valid_statuses = dict(Booking.STATUS_CHOICES)
    if new_status not in valid_statuses:
        return JsonResponse(
            {'success': False, 'error': 'Invalid booking status.'},
            status=400,
        )

    old_status = booking.status
    booking.status = new_status

    if new_status == Booking.STATUS_CANCELLED:
        booking.cancellation_reason = request.POST.get('reason', '').strip()

    booking.save(update_fields=[
        'status', 'cancellation_reason', 'updated_at',
    ])

    # Auto-create wash job when ARRIVED or CONFIRMED
    if new_status in [Booking.STATUS_ARRIVED, Booking.STATUS_CONFIRMED]:
        if old_status not in [Booking.STATUS_ARRIVED, Booking.STATUS_CONFIRMED]:
            try:
                from apps.wash.models import WashJob, WashJobItem
                existing = WashJob.objects.filter(booking=booking).first()
                if not existing:
                    wash_job = WashJob.objects.create(
                        booking    = booking,
                        customer   = booking.customer,
                        vehicle    = booking.vehicle,
                        service    = booking.service,
                        branch     = booking.branch,
                        wash_bay   = booking.wash_bay,
                        assigned_employee = booking.assigned_employee,
                        status     = WashJob.STATUS_WAITING,
                        created_by = request.user,
                        notes      = booking.notes,
                    )

                    # Auto-add service as item
                    if booking.service:
                        price = booking.service.get_price_amount(
                            vehicle_type=booking.vehicle.vehicle_type if booking.vehicle else None,
                            branch=booking.branch,
                        )
                        WashJobItem.objects.create(
                            wash_job=wash_job,
                            item_type='service',
                            name=booking.service.name,
                            quantity=1,
                            unit_price=price,
                            service=booking.service,
                            vat_applicable=True,
                        )
            except Exception as e:
                logger.warning(f'Failed to auto-create wash job: {e}')

    AuditLog.log(
        action='BOOKING_STATUS_CHANGED',
        module='bookings',
        user=request.user,
        object_type='Booking',
        object_id=booking.pk,
        object_repr=str(booking),
        previous_data={'status': old_status},
        new_data={'status': new_status},
        ip_address=client_ip(request),
    )

    return JsonResponse({
        'success': True,
        'message': 'Booking status updated.',
        'status':  new_status,
        'status_label': valid_statuses[new_status],
    })


# ─── BOOKING SEARCH ───────────────────────────────────────────

@login_required
def booking_search_ajax(request):
    query = request.GET.get('q', '').strip()

    if not query:
        return JsonResponse({'bookings': []})

    bookings = Booking.objects.filter(
        Q(booking_number__icontains=query)
        | Q(customer__name__icontains=query)
        | Q(vehicle__registration_number__icontains=query)
    ).select_related(
        'customer',
        'vehicle',
        'service',
    ).order_by(
        'scheduled_date',
        'scheduled_time',
    )[:20]

    return JsonResponse({
        'bookings': [
            {
                'id': booking.pk,
                'booking_number': booking.booking_number,
                'customer': booking.customer.name,
                'vehicle': booking.vehicle.registration_number,
                'service': booking.service.name,
                'date': str(booking.scheduled_date),
                'time': str(booking.scheduled_time),
                'status': booking.status,
            }
            for booking in bookings
        ],
    })


# ─── AJAX Endpoints for SmartInputs ───────────────────────────

@login_required
def service_search_ajax(request):
    q = request.GET.get('q', '').strip()
    show_all = request.GET.get('all', '') == '1'

    from apps.services.models import Service
    services = Service.objects.filter(is_deleted=False, is_active=True)
    if q:
        services = services.filter(name__icontains=q)

    limit = 50 if show_all else 20
    services = services.select_related('category').order_by('name')[:limit]

    data = [
        {
            'id':       s.pk,
            'label':    s.name,
            'name':     s.name,
            'duration': s.duration_minutes,
            'meta':     s.category.name if s.category else '',
        }
        for s in services
    ]
    return JsonResponse({'services': data})


@login_required
@require_http_methods(['POST'])
def service_create_ajax(request):
    """Auto-create service from smart input."""
    if not check_permission(request, PermissionCode.SERVICES_MANAGE):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'},
            status=403
        )

    from apps.services.models import Service
    from django.conf import settings
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse(
            {'success': False, 'error': 'Name required.'},
            status=400
        )

    existing = Service.objects.filter(
        name__iexact=name, is_deleted=False
    ).first()
    created = False
    if not existing:
        existing = Service.objects.create(
            name=name,
            is_active=True,
            duration_minutes=getattr(settings, 'DEFAULT_SERVICE_DURATION', 30),
            created_by=request.user,
        )
        created = True

    return JsonResponse({
        'success': True,
        'item': {
            'id':    existing.pk,
            'label': existing.name,
            'name':  existing.name,
        },
        'created': created,
        'message': (
            f'Service "{existing.name}" added.' if created
            else f'"{existing.name}" already exists — selected.'
        ),
    })

@login_required
def branch_search_ajax(request):
    q = request.GET.get('q', '').strip()
    show_all = request.GET.get('all', '') == '1'

    from apps.branches.models import Branch
    branches = Branch.objects.filter(status='active')
    if q:
        branches = branches.filter(name__icontains=q)
    limit = 50 if show_all else 20
    branches = branches.order_by('name')[:limit]

    data = [
        {'id': b.pk, 'label': b.name, 'name': b.name, 'meta': b.code}
        for b in branches
    ]
    return JsonResponse({'branches': data})


@login_required
def employee_search_ajax(request):
    q = request.GET.get('q', '').strip()
    show_all = request.GET.get('all', '') == '1'

    from django.contrib.auth.models import User
    users = User.objects.filter(is_active=True)
    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)
        )
    limit = 50 if show_all else 20
    users = users.order_by('username')[:limit]

    data = [
        {
            'id':    u.pk,
            'label': u.get_full_name() or u.username,
            'name':  u.get_full_name() or u.username,
            'meta':  u.username,
        }
        for u in users
    ]
    return JsonResponse({'employees': data})


@login_required
def wash_bay_search_ajax(request):
    q         = request.GET.get('q', '').strip()
    branch_id = request.GET.get('branch_id', '')
    show_all  = request.GET.get('all', '') == '1'

    from apps.wash.models import WashBay
    bays = WashBay.objects.filter(is_active=True)
    if branch_id:
        bays = bays.filter(branch_id=branch_id)
    if q:
        bays = bays.filter(Q(name__icontains=q) | Q(code__icontains=q))

    limit = 50 if show_all else 20
    bays = bays.select_related('branch').order_by('branch__name', 'name')[:limit]

    data = [
        {
            'id':    b.pk,
            'label': b.name,
            'name':  b.name,
            'meta':  f'{b.branch.name} · {b.code}',
        }
        for b in bays
    ]
    return JsonResponse({'wash_bays': data})


@login_required
@require_http_methods(['POST'])
def wash_bay_create_ajax(request):
    """Auto-create wash bay."""
    if not check_permission(request, PermissionCode.BOOKINGS_MANAGE):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'},
            status=403
        )

    from apps.wash.models import WashBay
    from apps.branches.models import Branch

    name      = request.POST.get('name', '').strip().upper()
    branch_id = request.POST.get('branch_id', '')

    if not name:
        return JsonResponse(
            {'success': False, 'error': 'Bay name required.'},
            status=400
        )

    branch = Branch.objects.filter(pk=branch_id).first() if branch_id else None
    if not branch:
        branch = Branch.objects.filter(is_default=True).first()
    if not branch:
        return JsonResponse(
            {'success': False, 'error': 'Please select a branch first.'},
            status=400
        )

    # Generate code from name
    code = name.replace(' ', '')[:20]

    existing = WashBay.objects.filter(
        branch=branch, code__iexact=code
    ).first()
    created = False
    if not existing:
        existing = WashBay.objects.create(
            branch=branch, name=name, code=code, is_active=True
        )
        created = True

    return JsonResponse({
        'success': True,
        'item': {
            'id':    existing.pk,
            'label': existing.name,
            'name':  existing.name,
            'meta':  f'{branch.name}',
        },
        'created': created,
        'message': (
            f'Wash bay "{existing.name}" added.' if created
            else f'"{existing.name}" already exists — selected.'
        ),
    })


@login_required
def customer_vehicles_ajax(request):
    """Get all vehicles for a customer (for filtering)."""
    customer_id = request.GET.get('customer_id', '')

    from apps.vehicles.models import Vehicle
    vehicles = Vehicle.objects.filter(
        customer_id=customer_id,
        is_deleted=False,
        status='active',
    ).select_related('brand', 'model')

    data = [
        {
            'id':                  v.pk,
            'label':               v.registration_number,
            'registration_number': v.registration_number,
            'brand_id':            v.brand_id,
            'brand':               v.brand.name,
            'model_id':            v.model_id,
            'model':               v.model.name,
            'meta':                f'{v.brand.name} {v.model.name}',
        }
        for v in vehicles
    ]
    return JsonResponse({'vehicles': data})


@login_required
def vehicle_full_details_ajax(request, pk):
    """Get full vehicle details for auto-fill."""
    from apps.vehicles.models import Vehicle
    v = Vehicle.objects.filter(
        pk=pk, is_deleted=False
    ).select_related(
        'customer', 'brand', 'model', 'vehicle_type', 'color', 'fuel_type'
    ).first()

    if not v:
        return JsonResponse({'success': False}, status=404)

    return JsonResponse({
        'success': True,
        'vehicle': {
            'id':                  v.pk,
            'registration_number': v.registration_number,
            'customer_id':         v.customer_id,
            'customer_name':       v.customer.name,
            'customer_phone':      v.customer.phone,
            'customer_code':       v.customer.customer_code,
            'brand':               v.brand.name,
            'model':               v.model.name,
            'vehicle_type':        v.vehicle_type.name if v.vehicle_type else '',
            'color':               v.color.name if v.color else '',
            'fuel_type':           v.fuel_type.name if v.fuel_type else '',
            'year':                v.year,
        }
    })


# ─── Helper: Resolve Pending Items ────────────────────────────

def _resolve_booking_pending(request):
    """Convert pending service/wash_bay names into IDs."""
    from apps.services.models import Service
    from apps.wash.models import WashBay
    from apps.branches.models import Branch

    post = request.POST.copy()

    # Service
    if not post.get('service') and post.get('service_new'):
        name = post['service_new'].strip()
        if name:
            existing = Service.objects.filter(
                name__iexact=name, is_deleted=False
            ).first()
            if not existing:
                existing = Service.objects.create(
                    name=name, is_active=True,
                    duration_minutes=30,
                    created_by=request.user,
                )
            post['service'] = str(existing.pk)

    # Wash Bay
    if not post.get('wash_bay') and post.get('wash_bay_new'):
        name = post['wash_bay_new'].strip().upper()
        branch_id = post.get('branch', '')
        if name and branch_id:
            branch = Branch.objects.filter(pk=branch_id).first()
            if branch:
                code = name.replace(' ', '')[:20]
                existing = WashBay.objects.filter(
                    branch=branch, code__iexact=code
                ).first()
                if not existing:
                    existing = WashBay.objects.create(
                        branch=branch, name=name, code=code, is_active=True,
                    )
                post['wash_bay'] = str(existing.pk)

    return post


# ─── VEHICLE QUICK CREATE (from booking) ──────────────────────

@login_required
@require_http_methods(['POST'])
def vehicle_quick_create_ajax(request):
    """Quick create a vehicle from booking page popup."""
    if not check_permission(request, PermissionCode.BOOKINGS_MANAGE):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'},
            status=403
        )

    from apps.vehicles.models import (
        Vehicle, Brand, VehicleModel,
        VehicleType, Color, FuelType
    )
    from apps.customers.models import Customer

    customer_id = request.POST.get('customer_id', '').strip()
    registration = request.POST.get('registration_number', '').strip().upper()
    brand_id = request.POST.get('brand_id', '').strip()
    brand_new = request.POST.get('brand_new', '').strip().upper()
    model_id = request.POST.get('model_id', '').strip()
    model_new = request.POST.get('model_new', '').strip().upper()
    type_id = request.POST.get('vehicle_type_id', '').strip()
    type_new = request.POST.get('vehicle_type_new', '').strip().upper()
    color_id = request.POST.get('color_id', '').strip()
    color_new = request.POST.get('color_new', '').strip().upper()
    fuel_id = request.POST.get('fuel_type_id', '').strip()
    fuel_new = request.POST.get('fuel_type_new', '').strip().upper()
    year = request.POST.get('year', '').strip()

    # Validation
    if not customer_id:
        return JsonResponse(
            {'success': False, 'error': 'Customer is required.'},
            status=400
        )
    if not registration:
        return JsonResponse(
            {'success': False, 'error': 'Registration is required.'},
            status=400
        )
    if not brand_id and not brand_new:
        return JsonResponse(
            {'success': False, 'error': 'Brand is required.'},
            status=400
        )
    if not model_id and not model_new:
        return JsonResponse(
            {'success': False, 'error': 'Model is required.'},
            status=400
        )

    try:
        customer = Customer.objects.get(pk=customer_id, is_deleted=False)
    except Customer.DoesNotExist:
        return JsonResponse(
            {'success': False, 'error': 'Customer not found.'},
            status=400
        )

    # Check if registration exists
    existing = Vehicle.objects.filter(
        registration_number__iexact=registration,
        is_deleted=False,
    ).first()
    if existing:
        return JsonResponse({
            'success': False,
            'error': (
                f'Vehicle {registration} already exists '
                f'(owner: {existing.customer.name}).'
            ),
        }, status=400)

    try:
        with transaction.atomic():

            # Brand
            if brand_id:
                brand = Brand.objects.get(pk=brand_id)
            else:
                brand, _ = Brand.get_or_create_safe(brand_new)

            # Model
            if model_id:
                vehicle_model = VehicleModel.objects.get(pk=model_id)
            else:
                vehicle_model, _ = VehicleModel.get_or_create_safe(
                    brand, model_new
                )

            # Vehicle Type (optional)
            vehicle_type = None
            if type_id:
                vehicle_type = VehicleType.objects.filter(pk=type_id).first()
            elif type_new:
                vehicle_type = VehicleType.objects.filter(
                    name__iexact=type_new
                ).first()
                if not vehicle_type:
                    vehicle_type = VehicleType.objects.create(
                        name=type_new, is_active=True
                    )

            # Color (optional)
            color = None
            if color_id:
                color = Color.objects.filter(pk=color_id).first()
            elif color_new:
                color = Color.objects.filter(name__iexact=color_new).first()
                if not color:
                    color = Color.objects.create(
                        name=color_new, is_active=True
                    )

            # Fuel Type (optional)
            fuel_type = None
            if fuel_id:
                fuel_type = FuelType.objects.filter(pk=fuel_id).first()
            elif fuel_new:
                fuel_type = FuelType.objects.filter(
                    name__iexact=fuel_new
                ).first()
                if not fuel_type:
                    fuel_type = FuelType.objects.create(
                        name=fuel_new, is_active=True
                    )

            # Create vehicle
            vehicle = Vehicle.objects.create(
                customer=customer,
                registration_number=registration,
                brand=brand,
                model=vehicle_model,
                vehicle_type=vehicle_type,
                color=color,
                fuel_type=fuel_type,
                year=int(year) if year else None,
                status='active',
                created_by=request.user,
            )

            AuditLog.log(
                action='VEHICLE_CREATED',
                module='vehicles',
                user=request.user,
                object_type='Vehicle',
                object_id=vehicle.pk,
                object_repr=str(vehicle),
                new_data={
                    'registration_number': registration,
                    'brand':  brand.name,
                    'model':  vehicle_model.name,
                    'customer': customer.name,
                    'source': 'booking_page_popup',
                },
                ip_address=client_ip(request),
            )

    except Exception as e:
        logger.exception('Vehicle quick create failed')
        return JsonResponse(
            {'success': False, 'error': f'Failed: {e}'},
            status=500
        )

    return JsonResponse({
        'success': True,
        'item': {
            'id':                  vehicle.pk,
            'label':               vehicle.registration_number,
            'registration_number': vehicle.registration_number,
            'brand':               brand.name,
            'model':               vehicle_model.name,
            'meta':                f'{brand.name} {vehicle_model.name}',
        },
        'vehicle_details': {
            'brand':        brand.name,
            'model':        vehicle_model.name,
            'vehicle_type': vehicle_type.name if vehicle_type else '',
            'color':        color.name if color else '',
            'fuel_type':    fuel_type.name if fuel_type else '',
            'year':         vehicle.year,
        },
        'message': f'Vehicle {registration} added successfully.',
    })