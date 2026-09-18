"""
AquaFlow — Role & Permission Management
Powered by Quantum Axis

Super Admin only. Create custom roles, assign permissions.
"""

import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Role, RolePermission, UserProfile, RoleCode, PermissionCode
from apps.system.models import AuditLog

logger = logging.getLogger('apps')


def is_super_admin(request):
    try:
        return request.user.profile.role.code == RoleCode.SUPER_ADMIN
    except Exception:
        return False


def client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ─── PERMISSION GROUPS (for UI display) ─────────────────────

PERMISSION_GROUPS = {
    'Point of Sale': [
        (PermissionCode.POS_ACCESS,   'Access POS'),
        (PermissionCode.POS_DISCOUNT, 'Apply Discounts'),
        (PermissionCode.POS_REFUND,   'Process Refunds'),
    ],
    'Customers': [
        (PermissionCode.CUSTOMERS_VIEW,   'View Customers'),
        (PermissionCode.CUSTOMERS_CREATE, 'Create Customers'),
        (PermissionCode.CUSTOMERS_EDIT,   'Edit Customers'),
        (PermissionCode.CUSTOMERS_DELETE, 'Delete Customers'),
    ],
    'Vehicles': [
        (PermissionCode.VEHICLES_VIEW,   'View Vehicles'),
        (PermissionCode.VEHICLES_CREATE, 'Create Vehicles'),
        (PermissionCode.VEHICLES_EDIT,   'Edit Vehicles'),
        (PermissionCode.VEHICLES_DELETE, 'Delete Vehicles'),
    ],
    'Services': [
        (PermissionCode.SERVICES_VIEW,   'View Services'),
        (PermissionCode.SERVICES_MANAGE, 'Manage Services & Pricing'),
    ],
    'Bookings': [
        (PermissionCode.BOOKINGS_VIEW,   'View Bookings'),
        (PermissionCode.BOOKINGS_MANAGE, 'Manage Bookings'),
    ],
    'Orders & Invoices': [
        (PermissionCode.ORDERS_VIEW,   'View Orders'),
        (PermissionCode.ORDERS_VOID,   'Void Orders'),
        (PermissionCode.INVOICES_VIEW, 'View Invoices'),
        (PermissionCode.INVOICES_VOID, 'Void Invoices'),
    ],
    'Wash Operations': [
        (PermissionCode.WASH_VIEW,   'View Wash Board'),
        (PermissionCode.WASH_MANAGE, 'Manage Wash Jobs'),
    ],
    'Inventory': [
        (PermissionCode.INVENTORY_VIEW,   'View Inventory'),
        (PermissionCode.INVENTORY_MANAGE, 'Manage Inventory'),
        (PermissionCode.INVENTORY_ADJUST, 'Adjust Stock'),
    ],
    'Suppliers': [
        (PermissionCode.SUPPLIERS_VIEW,   'View Suppliers'),
        (PermissionCode.SUPPLIERS_MANAGE, 'Manage Suppliers'),
    ],
    'Employees': [
        (PermissionCode.EMPLOYEES_VIEW,   'View Employees'),
        (PermissionCode.EMPLOYEES_MANAGE, 'Manage Employees'),
    ],
    'Finance': [
        (PermissionCode.FINANCE_VIEW,   'View Finance/Expenses'),
        (PermissionCode.FINANCE_MANAGE, 'Manage Expenses'),
    ],
    'Memberships': [
        (PermissionCode.MEMBERSHIPS_VIEW,   'View Memberships'),
        (PermissionCode.MEMBERSHIPS_MANAGE, 'Manage Memberships'),
    ],
    'Reports': [
        (PermissionCode.REPORTS_VIEW,   'View Reports'),
        (PermissionCode.REPORTS_EXPORT, 'Export Reports'),
    ],
    'System': [
        (PermissionCode.SYSTEM_HEALTH,   'View System Health'),
        (PermissionCode.SYSTEM_SETTINGS, 'Manage System Settings'),
        (PermissionCode.BUSINESS_CONFIGURE, 'Configure Business'),
        (PermissionCode.BRANCH_MANAGE, 'Manage Branches'),
        (PermissionCode.USERS_MANAGE,  'Manage Users'),
        (PermissionCode.ROLES_MANAGE,  'Manage Roles'),
    ],
    'Backup & Recovery': [
        (PermissionCode.BACKUP_CREATE,   'Create Backups'),
        (PermissionCode.BACKUP_VIEW,     'View Backups'),
        (PermissionCode.BACKUP_DOWNLOAD, 'Download Backups'),
        (PermissionCode.BACKUP_DELETE,   'Delete Backups'),
        (PermissionCode.BACKUP_RESTORE,  'Restore Backups'),
        (PermissionCode.BACKUP_SCHEDULE, 'Schedule Backups'),
    ],
    'Trash & Audit': [
        (PermissionCode.TRASH_VIEW,        'View Trash'),
        (PermissionCode.TRASH_RESTORE,     'Restore from Trash'),
        (PermissionCode.TRASH_PERM_DELETE, 'Permanently Delete'),
        (PermissionCode.AUDIT_VIEW,        'View Audit Logs'),
    ],
    'Database (Super Admin)': [
        (PermissionCode.DATABASE_VIEW,      'View DB Config'),
        (PermissionCode.DATABASE_TEST,      'Test DB Connection'),
        (PermissionCode.DATABASE_CONFIGURE, 'Configure Database'),
    ],
}


# ─── ROLE LIST ───────────────────────────────────────────────

@login_required
def role_list(request):
    if not is_super_admin(request):
        messages.error(request, 'Only Super Admin can manage roles.')
        return redirect('dashboard')

    roles = Role.objects.annotate(
        user_count=Count('users'),
        permission_count=Count('role_permissions'),
    ).order_by('is_system', 'name')

    total_permissions = len(list(PermissionCode))

    context = {
        'page_title':        'Roles & Permissions',
        'roles':             roles,
        'total_permissions': total_permissions,
    }
    return render(request, 'accounts/role_list.html', context)


# ─── ROLE CREATE ─────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def role_create(request):
    if not is_super_admin(request):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    copy_from = request.POST.get('copy_from', '').strip()

    if not name:
        return JsonResponse({'success': False, 'error': 'Name required.'}, status=400)

    # Generate code from name (uppercase, underscore)
    code = name.upper().replace(' ', '_')
    code = ''.join(c for c in code if c.isalnum() or c == '_')[:50]

    if not code:
        return JsonResponse({'success': False, 'error': 'Invalid name.'}, status=400)

    # Check duplicate
    if Role.objects.filter(Q(code=code) | Q(name__iexact=name)).exists():
        return JsonResponse({
            'success': False,
            'error': f'A role with this name already exists.',
        }, status=400)

    try:
        with transaction.atomic():
            role = Role.objects.create(
                code=code,
                name=name,
                description=description,
                is_system=False,  # Custom roles are never system
            )

            # Copy permissions if requested
            if copy_from:
                source = Role.objects.filter(pk=copy_from).first()
                if source:
                    for perm in source.role_permissions.all():
                        RolePermission.objects.create(
                            role=role,
                            permission=perm.permission,
                        )

            AuditLog.log(
                action='ROLE_CREATED',
                module='security',
                user=request.user,
                object_type='Role',
                object_id=role.pk,
                object_repr=role.name,
                new_data={
                    'name': name,
                    'code': code,
                    'copied_from': copy_from or None,
                },
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'Role "{name}" created. Configure permissions next.',
            'role_id': role.pk,
        })
    except Exception as e:
        logger.exception('Role create failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─── ROLE EDIT (Permissions) ─────────────────────────────────

@login_required
def role_edit(request, pk):
    if not is_super_admin(request):
        messages.error(request, 'Only Super Admin can edit roles.')
        return redirect('role_list')

    role = get_object_or_404(Role, pk=pk)

    # Get current permissions
    current_perms = set(role.role_permissions.values_list('permission', flat=True))

    context = {
        'page_title':       f'Edit Role — {role.name}',
        'role':             role,
        'current_perms':    current_perms,
        'permission_groups': PERMISSION_GROUPS,
        'is_super_admin_role': role.code == RoleCode.SUPER_ADMIN,
    }
    return render(request, 'accounts/role_edit.html', context)


@login_required
@require_http_methods(['POST'])
def role_update(request, pk):
    if not is_super_admin(request):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    role = get_object_or_404(Role, pk=pk)

    # Cannot modify Super Admin permissions (they have all by default)
    if role.code == RoleCode.SUPER_ADMIN:
        # Allow name/description edit but not permissions
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if name:
            role.name = name
        role.description = description
        role.save(update_fields=['name', 'description', 'updated_at'])
        return JsonResponse({
            'success': True,
            'message': 'Super Admin details updated. Permissions are always full.',
        })

    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    selected_perms = request.POST.getlist('permissions')

    if not name:
        return JsonResponse({'success': False, 'error': 'Name required.'}, status=400)

    try:
        with transaction.atomic():
            previous_perms = list(role.role_permissions.values_list('permission', flat=True))

            role.name = name
            role.description = description
            role.save()

            # Wipe and re-add permissions
            role.role_permissions.all().delete()

            valid_perms = {p.value for p in PermissionCode}
            for perm_code in selected_perms:
                if perm_code in valid_perms:
                    RolePermission.objects.create(
                        role=role,
                        permission=perm_code,
                    )

            AuditLog.log(
                action='ROLE_UPDATED',
                module='security',
                user=request.user,
                object_type='Role',
                object_id=role.pk,
                object_repr=role.name,
                previous_data={'permissions': previous_perms},
                new_data={
                    'permissions': selected_perms,
                    'name': name,
                },
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'Role "{role.name}" updated with {len(selected_perms)} permissions.',
        })
    except Exception as e:
        logger.exception('Role update failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─── ROLE DELETE ─────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def role_delete(request, pk):
    if not is_super_admin(request):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    role = get_object_or_404(Role, pk=pk)

    if role.is_system:
        return JsonResponse({
            'success': False,
            'error': 'Cannot delete system roles (SUPER_ADMIN, OWNER, MANAGER, CASHIER, WASHER, etc.).',
        }, status=400)

    user_count = role.users.count()
    if user_count > 0:
        return JsonResponse({
            'success': False,
            'error': f'Cannot delete — {user_count} user(s) currently assigned. Reassign users first.',
        }, status=400)

    role_name = role.name

    try:
        AuditLog.log(
            action='ROLE_DELETED',
            module='security',
            user=request.user,
            object_type='Role',
            object_id=role.pk,
            object_repr=role_name,
            ip_address=client_ip(request),
        )
        role.delete()

        return JsonResponse({
            'success': True,
            'message': f'Role "{role_name}" deleted.',
        })
    except Exception as e:
        logger.exception('Role delete failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ─── USER MANAGEMENT ─────────────────────────────────────────

@login_required
def user_list(request):
    """List all users with their roles."""
    if not is_super_admin(request):
        messages.error(request, 'Only Super Admin can manage users.')
        return redirect('dashboard')

    search = request.GET.get('q', '').strip()

    users = User.objects.select_related('profile__role').all()

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )

    users = users.order_by('username')

    roles = Role.objects.all().order_by('name')

    context = {
        'page_title': 'User Management',
        'users':      users,
        'search':     search,
        'roles':      roles,
    }
    return render(request, 'accounts/user_list.html', context)


@login_required
@require_http_methods(['POST'])
def user_create(request):
    if not is_super_admin(request):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    password = request.POST.get('password', '').strip()
    role_id = request.POST.get('role_id', '')

    if not username:
        return JsonResponse({'success': False, 'error': 'Username required.'}, status=400)
    if not password or len(password) < 8:
        return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters.'}, status=400)
    if not role_id:
        return JsonResponse({'success': False, 'error': 'Role required.'}, status=400)

    if User.objects.filter(username__iexact=username).exists():
        return JsonResponse({
            'success': False,
            'error': f'Username "{username}" is already taken.',
        }, status=400)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            # Assign role via profile
            role = Role.objects.get(pk=role_id)
            from apps.businesses.models import Business
            from apps.branches.models import Branch
            business = Business.objects.get(pk=1)
            branch = Branch.objects.filter(is_default=True).first()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.business = business
            profile.branch = branch
            profile.status = 'active'
            profile.save()

            # If Super Admin role, set Django superuser flags
            if role.code == RoleCode.SUPER_ADMIN:
                user.is_superuser = True
                user.is_staff = True
                user.save()

            AuditLog.log(
                action='USER_CREATED',
                module='security',
                user=request.user,
                object_type='User',
                object_id=user.pk,
                object_repr=user.username,
                new_data={
                    'username': username,
                    'email': email,
                    'role': role.name,
                },
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'User "{username}" created with role "{role.name}".',
        })
    except Exception as e:
        logger.exception('User create failed')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def user_change_role(request, user_id):
    if not is_super_admin(request):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    user = get_object_or_404(User, pk=user_id)
    role_id = request.POST.get('role_id', '')

    if not role_id:
        return JsonResponse({'success': False, 'error': 'Role required.'}, status=400)

    try:
        new_role = Role.objects.get(pk=role_id)
    except Role.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Role not found.'}, status=400)

    profile, _ = UserProfile.objects.get_or_create(user=user)
    old_role = profile.role

    # Prevent removing last Super Admin
    if old_role and old_role.code == RoleCode.SUPER_ADMIN and new_role.code != RoleCode.SUPER_ADMIN:
        super_admin_count = UserProfile.objects.filter(
            role__code=RoleCode.SUPER_ADMIN,
            status='active',
        ).count()
        if super_admin_count <= 1:
            return JsonResponse({
                'success': False,
                'error': 'Cannot demote the last Super Admin.',
            }, status=400)

    profile.role = new_role
    profile.save(update_fields=['role', 'updated_at'])

    # Update Django superuser flag
    if new_role.code == RoleCode.SUPER_ADMIN:
        user.is_superuser = True
        user.is_staff = True
    else:
        user.is_superuser = False
        user.is_staff = False
    user.save()

    AuditLog.log(
        action='USER_ROLE_CHANGED',
        module='security',
        user=request.user,
        object_type='User',
        object_id=user.pk,
        object_repr=user.username,
        previous_data={'role': old_role.name if old_role else None},
        new_data={'role': new_role.name},
        ip_address=client_ip(request),
    )

    return JsonResponse({
        'success': True,
        'message': f'User "{user.username}" role changed to "{new_role.name}".',
    })


@login_required
@require_http_methods(['POST'])
def user_toggle_active(request, user_id):
    if not is_super_admin(request):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    user = get_object_or_404(User, pk=user_id)

    if user.pk == request.user.pk:
        return JsonResponse({
            'success': False,
            'error': 'You cannot deactivate yourself.',
        }, status=400)

    # Prevent deactivating last Super Admin
    try:
        if user.profile.role.code == RoleCode.SUPER_ADMIN:
            active_super = UserProfile.objects.filter(
                role__code=RoleCode.SUPER_ADMIN,
                status='active',
                user__is_active=True,
            ).exclude(user=user).count()
            if active_super == 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Cannot deactivate the last active Super Admin.',
                }, status=400)
    except Exception:
        pass

    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])

    AuditLog.log(
        action='USER_TOGGLED_ACTIVE',
        module='security',
        user=request.user,
        object_type='User',
        object_id=user.pk,
        object_repr=user.username,
        new_data={'is_active': user.is_active},
        ip_address=client_ip(request),
    )

    return JsonResponse({
        'success': True,
        'message': f'User "{user.username}" {"activated" if user.is_active else "deactivated"}.',
        'is_active': user.is_active,
    })


@login_required
@require_http_methods(['POST'])
def user_reset_password(request, user_id):
    if not is_super_admin(request):
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    user = get_object_or_404(User, pk=user_id)
    new_password = request.POST.get('new_password', '').strip()

    if not new_password or len(new_password) < 8:
        return JsonResponse({
            'success': False,
            'error': 'Password must be at least 8 characters.',
        }, status=400)

    user.set_password(new_password)
    user.save()

    AuditLog.log(
        action='USER_PASSWORD_RESET',
        module='security',
        user=request.user,
        object_type='User',
        object_id=user.pk,
        object_repr=user.username,
        ip_address=client_ip(request),
    )

    return JsonResponse({
        'success': True,
        'message': f'Password reset for "{user.username}".',
    })