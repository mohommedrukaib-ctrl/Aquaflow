"""
AquaFlow — Wash Views (Updated)
Powered by Quantum Axis

Features:
- Wash board (kanban)
- Create wash job with multiple items
- If future date → auto-creates booking
- Customer/vehicle popups
- Search bookings
- Job note generation
- Status workflow
"""

import json
import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import WashJob, WashBay, WashJobItem, JobNote
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


# ─── WASH BOARD ──────────────────────────────────────────────

@login_required
def wash_board(request):
    if not check_permission(request, PermissionCode.WASH_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    branch_id = request.GET.get('branch', '')
    today = timezone.now().date()

    jobs = WashJob.objects.select_related(
        'customer', 'vehicle', 'vehicle__brand', 'vehicle__model',
        'service', 'wash_bay', 'assigned_employee', 'branch',
    ).filter(
        Q(status__in=[
            WashJob.STATUS_WAITING, WashJob.STATUS_ASSIGNED,
            WashJob.STATUS_WASHING, WashJob.STATUS_QUALITY_CHECK,
            WashJob.STATUS_READY,
        ]) | Q(status=WashJob.STATUS_COMPLETED, completed_at__date=today)
    )

    if branch_id:
        jobs = jobs.filter(branch_id=branch_id)

    columns = {
        'waiting':       jobs.filter(status=WashJob.STATUS_WAITING).order_by('created_at'),
        'assigned':      jobs.filter(status=WashJob.STATUS_ASSIGNED).order_by('created_at'),
        'washing':       jobs.filter(status=WashJob.STATUS_WASHING).order_by('started_at'),
        'quality_check': jobs.filter(status=WashJob.STATUS_QUALITY_CHECK).order_by('quality_check_at'),
        'ready':         jobs.filter(status=WashJob.STATUS_READY).order_by('-updated_at'),
        'completed':     jobs.filter(status=WashJob.STATUS_COMPLETED).order_by('-completed_at'),
    }

    # Pending bookings (not yet converted to wash jobs)
    from apps.bookings.models import Booking
    pending_bookings = Booking.objects.filter(
        scheduled_date=today,
        status__in=['pending', 'confirmed'],
    ).select_related('customer', 'vehicle', 'service').order_by('scheduled_time')

    from apps.branches.models import Branch
    branches = Branch.objects.filter(status='active')

    context = {
        'page_title':       'Car Wash Operations',
        'columns':          columns,
        'today':            today,
        'branches':         branches,
        'branch_id':        branch_id,
        'pending_bookings': pending_bookings,
        'can_manage':       check_permission(request, PermissionCode.WASH_MANAGE),
    }
    return render(request, 'wash/wash_board.html', context)


# ─── CREATE WASH JOB ─────────────────────────────────────────

@login_required
def wash_job_create(request):
    if not check_permission(request, PermissionCode.WASH_MANAGE):
        messages.error(request, 'Permission denied.')
        return redirect('wash_board')

    from apps.branches.models import Branch
    branches = Branch.objects.filter(status='active')

    context = {
        'page_title': 'New Car Wash Job',
        'branches':   branches,
        'today':      timezone.now().date(),
    }
    return render(request, 'wash/wash_job_form.html', context)


@login_required
@require_http_methods(['POST'])
def wash_job_create_ajax(request):
    """
    Create a wash job via AJAX.
    If scheduled_date is in the future → also creates a BOOKING.
    Accepts multiple items (services, repairs, products).
    """
    if not check_permission(request, PermissionCode.WASH_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid data.'}, status=400)

    customer_id    = payload.get('customer_id')
    vehicle_id     = payload.get('vehicle_id')
    branch_id      = payload.get('branch_id')
    scheduled_date = payload.get('scheduled_date', '')
    scheduled_time = payload.get('scheduled_time', '')
    priority       = payload.get('priority', 'normal')
    notes          = payload.get('notes', '').strip()
    items          = payload.get('items', [])
    estimated_time = payload.get('estimated_time', '').strip()

    if not customer_id:
        return JsonResponse({'success': False, 'error': 'Customer required.'}, status=400)
    if not vehicle_id:
        return JsonResponse({'success': False, 'error': 'Vehicle required.'}, status=400)
    if not branch_id:
        return JsonResponse({'success': False, 'error': 'Branch required.'}, status=400)

    from apps.customers.models import Customer
    from apps.vehicles.models import Vehicle
    from apps.services.models import Service
    from apps.branches.models import Branch
    from apps.bookings.models import Booking

    try:
        with transaction.atomic():
            customer = Customer.objects.get(pk=customer_id, is_deleted=False)
            vehicle  = Vehicle.objects.get(pk=vehicle_id, is_deleted=False)
            branch   = Branch.objects.get(pk=branch_id)

            # Auto-reassign vehicle to customer if different
            if vehicle.customer_id != customer.pk:
                vehicle.customer = customer
                vehicle.save(update_fields=['customer', 'updated_at'])
                logger.info(
                    f'Vehicle {vehicle.registration_number} reassigned to {customer.name}'
                )

            today = timezone.now().date()
            is_future = False

            if scheduled_date:
                try:
                    from datetime import datetime
                    sched_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
                    is_future = sched_date > today
                except ValueError:
                    sched_date = today
            else:
                sched_date = today

            # Find first service from items (for backward compat)
            first_service = None
            for item in items:
                if item.get('type') in ('service', 'repair') and item.get('service_id'):
                    try:
                        first_service = Service.objects.get(pk=item['service_id'])
                        break
                    except Service.DoesNotExist:
                        pass

            # If future date → create booking first
            booking = None
            if is_future:
                sched_time_str = scheduled_time or '09:00'
                from datetime import datetime as dt
                try:
                    sched_time = dt.strptime(sched_time_str, '%H:%M').time()
                except ValueError:
                    sched_time = dt.strptime('09:00', '%H:%M').time()

                from apps.businesses.models import Business
                booking = Booking.objects.create(
                    business=Business.objects.get(pk=1),
                    branch=branch,
                    customer=customer,
                    vehicle=vehicle,
                    service=first_service,
                    scheduled_date=sched_date,
                    scheduled_time=sched_time,
                    duration_minutes=first_service.duration_minutes if first_service else 30,
                    status=Booking.STATUS_CONFIRMED,
                    notes=notes,
                    created_by=request.user,
                )

            # Create wash job
            wash_job = WashJob.objects.create(
                booking=booking,
                customer=customer,
                vehicle=vehicle,
                service=first_service,
                branch=branch,
                priority=priority,
                notes=notes,
                status=WashJob.STATUS_WAITING,
                created_by=request.user,
            )

            # Set estimated completion
            if estimated_time:
                wash_job.notes = (wash_job.notes or '') + f'\nEstimated: {estimated_time}'
                wash_job.save(update_fields=['notes'])

            # Create items
            for item_data in items:
                item_name = item_data.get('name', '').strip()
                item_type = item_data.get('type', 'service')

                if not item_name:
                    continue

                try:
                    unit_price = Decimal(str(item_data.get('unit_price', 0)))
                    quantity   = Decimal(str(item_data.get('quantity', 1)))
                except (InvalidOperation, ValueError):
                    unit_price = Decimal('0')
                    quantity = Decimal('1')

                service_obj = None
                product_obj = None

                if item_data.get('service_id'):
                    try:
                        service_obj = Service.objects.get(pk=item_data['service_id'])
                    except Service.DoesNotExist:
                        pass

                if item_data.get('product_id'):
                    from apps.inventory.models import Product
                    try:
                        product_obj = Product.objects.get(pk=item_data['product_id'])
                    except Product.DoesNotExist:
                        pass

                WashJobItem.objects.create(
                    wash_job=wash_job,
                    item_type=item_type,
                    name=item_name,
                    quantity=quantity,
                    unit_price=unit_price,
                    vat_applicable=item_data.get('vat', True),
                    service=service_obj,
                    product=product_obj,
                    estimated_hours=Decimal(str(item_data.get('estimated_hours', 0))),
                    warranty_days=int(item_data.get('warranty_days', 0)),
                    technician_notes=item_data.get('technician_notes', ''),
                )

            AuditLog.log(
                action='WASH_JOB_CREATED',
                module='wash',
                user=request.user,
                object_type='WashJob',
                object_id=wash_job.pk,
                object_repr=wash_job.job_number,
                new_data={
                    'customer': customer.name,
                    'vehicle':  vehicle.registration_number,
                    'items':    len(items),
                    'is_booking': is_future,
                    'booking':  booking.booking_number if booking else None,
                },
                ip_address=client_ip(request),
            )

        result = {
            'success':    True,
            'message':    f'Car wash job {wash_job.job_number} created.',
            'job_id':     wash_job.pk,
            'job_number': wash_job.job_number,
        }

        if booking:
            result['message'] += f' Booking {booking.booking_number} created for {sched_date}.'
            result['booking_number'] = booking.booking_number

        return JsonResponse(result)

    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Customer not found.'}, status=400)
    except Vehicle.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vehicle not found.'}, status=400)
    except Branch.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Branch not found.'}, status=400)
    except Exception as e:
        logger.exception('Wash job create failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─── ADD ITEM TO EXISTING JOB ────────────────────────────────

@login_required
@require_http_methods(['POST'])
def wash_job_add_item(request, pk):
    if not check_permission(request, PermissionCode.WASH_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    job = get_object_or_404(WashJob, pk=pk)

    name       = request.POST.get('name', '').strip()
    item_type  = request.POST.get('type', 'service')
    unit_price = request.POST.get('unit_price', '0')
    quantity   = request.POST.get('quantity', '1')

    if not name:
        return JsonResponse({'success': False, 'error': 'Name required.'}, status=400)

    try:
        price = Decimal(str(unit_price))
        qty   = Decimal(str(quantity))
    except (InvalidOperation, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid values.'}, status=400)

    item = WashJobItem.objects.create(
        wash_job=job,
        item_type=item_type,
        name=name,
        quantity=qty,
        unit_price=price,
        vat_applicable=True,
    )

    return JsonResponse({
        'success': True,
        'message': f'Item "{name}" added.',
        'item': {
            'id':         item.pk,
            'name':       item.name,
            'type':       item.item_type,
            'unit_price': str(item.unit_price),
            'quantity':   str(item.quantity),
            'total':      str(item.total),
        },
    })


# ─── WASH JOB DETAIL ─────────────────────────────────────────

@login_required
def wash_job_detail(request, pk):
    if not check_permission(request, PermissionCode.WASH_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    job = get_object_or_404(
        WashJob.objects.select_related(
            'customer', 'vehicle', 'vehicle__brand', 'vehicle__model',
            'service', 'wash_bay', 'assigned_employee', 'branch',
            'booking', 'order', 'invoice',
        ).prefetch_related('items'),
        pk=pk
    )

    employees = User.objects.filter(is_active=True).order_by('username')
    bays      = WashBay.objects.filter(branch=job.branch, is_active=True)

    context = {
        'page_title': job.job_number,
        'job':        job,
        'items':      job.items.all(),
        'employees':  employees,
        'bays':       bays,
        'can_manage': check_permission(request, PermissionCode.WASH_MANAGE),
    }
    return render(request, 'wash/wash_job_detail.html', context)


# ─── UPDATE STATUS ───────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def update_status(request, pk):
    if not check_permission(request, PermissionCode.WASH_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    job = get_object_or_404(WashJob, pk=pk)
    new_status = request.POST.get('status', '').strip()

    valid_statuses = dict(WashJob.STATUS_CHOICES)
    if new_status not in valid_statuses:
        return JsonResponse({'success': False, 'error': 'Invalid status.'}, status=400)

    old_status = job.status
    now = timezone.now()

    try:
        with transaction.atomic():
            job.status = new_status

            if new_status == WashJob.STATUS_WASHING and not job.started_at:
                job.started_at = now
                if job.wash_bay:
                    job.wash_bay.status = WashBay.STATUS_OCCUPIED
                    job.wash_bay.save(update_fields=['status'])

            if new_status == WashJob.STATUS_QUALITY_CHECK and not job.quality_check_at:
                job.quality_check_at = now

            if new_status in [WashJob.STATUS_READY, WashJob.STATUS_COMPLETED]:
                if not job.completed_at:
                    job.completed_at = now
                if job.wash_bay:
                    job.wash_bay.status = WashBay.STATUS_AVAILABLE
                    job.wash_bay.save(update_fields=['status'])

            job.save()

            AuditLog.log(
                action='WASH_JOB_STATUS_CHANGED',
                module='wash',
                user=request.user,
                object_type='WashJob',
                object_id=job.pk,
                object_repr=job.job_number,
                previous_data={'status': old_status},
                new_data={'status': new_status},
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success':      True,
            'message':      f'Status updated to {valid_statuses[new_status]}.',
            'status':       new_status,
            'status_label': valid_statuses[new_status],
        })
    except Exception as e:
        logger.exception('Status update failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─── ASSIGN EMPLOYEE ─────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def assign_employee(request, pk):
    if not check_permission(request, PermissionCode.WASH_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    job = get_object_or_404(WashJob, pk=pk)
    employee_id = request.POST.get('employee_id')

    if not employee_id:
        job.assigned_employee = None
        if job.status == WashJob.STATUS_ASSIGNED:
            job.status = WashJob.STATUS_WAITING
        job.save(update_fields=['assigned_employee', 'status', 'updated_at'])
        return JsonResponse({'success': True, 'message': 'Employee unassigned.'})

    try:
        employee = User.objects.get(pk=employee_id, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Employee not found.'}, status=400)

    job.assigned_employee = employee
    if job.status == WashJob.STATUS_WAITING:
        job.status = WashJob.STATUS_ASSIGNED
    job.save(update_fields=['assigned_employee', 'status', 'updated_at'])

    return JsonResponse({
        'success': True,
        'message': f'Assigned to {employee.get_full_name() or employee.username}.',
    })


# ─── ASSIGN BAY ──────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def assign_bay(request, pk):
    if not check_permission(request, PermissionCode.WASH_MANAGE):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    job = get_object_or_404(WashJob, pk=pk)
    bay_id = request.POST.get('bay_id')

    if not bay_id:
        job.wash_bay = None
        job.save(update_fields=['wash_bay', 'updated_at'])
        return JsonResponse({'success': True, 'message': 'Bay unassigned.'})

    try:
        bay = WashBay.objects.get(pk=bay_id, is_active=True)
    except WashBay.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Bay not found.'}, status=400)

    job.wash_bay = bay
    job.save(update_fields=['wash_bay', 'updated_at'])

    return JsonResponse({'success': True, 'message': f'Bay {bay.name} assigned.'})


# ─── GENERATE JOB NOTE ───────────────────────────────────────

@login_required
def generate_job_note(request, pk):
    if not check_permission(request, PermissionCode.WASH_MANAGE):
        messages.error(request, 'Permission denied.')
        return redirect('wash_board')

    job = get_object_or_404(
        WashJob.objects.select_related('customer', 'vehicle', 'vehicle__brand', 'vehicle__model'),
        pk=pk
    )

    # Create or get existing note
    try:
        note = job.job_note
    except JobNote.DoesNotExist:
        note = JobNote.create_from_wash_job(job, user=request.user)

    note.printed_at = timezone.now()
    note.save(update_fields=['printed_at'])

    from apps.businesses.models import Business
    business = Business.objects.get(pk=1)

    fmt = request.GET.get('format', getattr(business, 'job_note_format', 'thermal_80mm'))

    template_map = {
        'thermal_80mm': 'wash/job_note_thermal.html',
        'half_a4_bw':   'wash/job_note_half_a4.html',
    }

    template = template_map.get(fmt, 'wash/job_note_thermal.html')

    context = {
        'note':     note,
        'job':      job,
        'items':    job.items.all(),
        'business': business,
        'formats': [
            ('thermal_80mm', 'Thermal (80mm)'),
            ('half_a4_bw',   'Half A4 (B&W)'),
        ],
        'current_format': fmt,
    }
    return render(request, template, context)


# ─── WASH JOB LIST ────────────────────────────────────────────

@login_required
def wash_job_list(request):
    if not check_permission(request, PermissionCode.WASH_VIEW):
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    search    = request.GET.get('q', '').strip()
    status    = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')

    jobs = WashJob.objects.select_related(
        'customer', 'vehicle', 'service', 'wash_bay', 'assigned_employee', 'branch',
    )

    if search:
        jobs = jobs.filter(
            Q(job_number__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(vehicle__registration_number__icontains=search)
        )

    if status:
        jobs = jobs.filter(status=status)

    if date_from:
        jobs = jobs.filter(created_at__date__gte=date_from)
    if date_to:
        jobs = jobs.filter(created_at__date__lte=date_to)

    jobs = jobs.order_by('-created_at')

    paginator = Paginator(jobs, 30)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_title':     'Wash Jobs',
        'page_obj':       page_obj,
        'jobs':           page_obj,
        'search':         search,
        'status':         status,
        'date_from':      date_from,
        'date_to':        date_to,
        'total_count':    paginator.count,
        'status_choices': WashJob.STATUS_CHOICES,
    }
    return render(request, 'wash/wash_job_list.html', context)


# ─── AJAX: Wash Board Data ───────────────────────────────────

@login_required
def wash_board_data(request):
    if not check_permission(request, PermissionCode.WASH_VIEW):
        return JsonResponse({'success': False}, status=403)

    today = timezone.now().date()

    jobs = WashJob.objects.filter(
        Q(status__in=[
            WashJob.STATUS_WAITING, WashJob.STATUS_ASSIGNED,
            WashJob.STATUS_WASHING, WashJob.STATUS_QUALITY_CHECK,
            WashJob.STATUS_READY,
        ]) | Q(status=WashJob.STATUS_COMPLETED, completed_at__date=today)
    )

    return JsonResponse({
        'success': True,
        'counts': {
            s: jobs.filter(status=s).count()
            for s in ['waiting', 'assigned', 'washing', 'quality_check', 'ready', 'completed']
        },
    })