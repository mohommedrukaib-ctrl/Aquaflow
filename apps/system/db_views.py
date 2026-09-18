"""
AquaFlow — Database Configuration Views
Powered by Quantum Axis

Super Admin only. Password never exposed in responses.
"""

import logging
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings

from apps.accounts.models import RoleCode
from apps.system.models import DatabaseConfig, AuditLog
from apps.system.db_service import DatabaseService

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


# ─── DATABASE CONFIG PAGE ────────────────────────────────────

@login_required
def db_config_page(request):
    if not is_super_admin(request):
        messages.error(
            request,
            'Only Super Admin can access database configuration.'
        )
        return redirect('dashboard')

    # Current active config
    current = settings.DATABASES['default']

    # Get last known good config
    last_good = DatabaseConfig.objects.filter(
        is_last_known_good=True
    ).first()

    # Get all saved configs (excluding password)
    saved_configs = DatabaseConfig.objects.all().order_by('-created_at')[:10]

    context = {
        'page_title':  'Database Configuration',
        'current': {
            'engine':   current.get('ENGINE', ''),
            'host':     current.get('HOST', ''),
            'port':     current.get('PORT', ''),
            'db_name':  current.get('NAME', ''),
            'username': current.get('USER', ''),
            'ssl_mode': current.get('OPTIONS', {}).get('sslmode', 'prefer'),
        },
        'last_good':     last_good,
        'saved_configs': saved_configs,
        'ssl_choices':   DatabaseConfig.SSL_CHOICES,
    }
    return render(request, 'system/db_config.html', context)


# ─── TEST CONNECTION ─────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def db_test_connection(request):
    if not is_super_admin(request):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'},
            status=403
        )

    host     = request.POST.get('host', '').strip()
    port     = request.POST.get('port', '5432').strip()
    db_name  = request.POST.get('db_name', '').strip()
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()
    ssl_mode = request.POST.get('ssl_mode', 'prefer').strip()

    # Use existing password if empty
    use_existing_pw = request.POST.get('use_existing_password') == '1'
    if use_existing_pw:
        current = DatabaseConfig.objects.filter(is_active=True).first()
        if current:
            password = current.get_password()

    if not all([host, port, db_name, username]):
        return JsonResponse({
            'success': False,
            'error': 'Host, port, database, and username are required.',
        }, status=400)

    if not password:
        return JsonResponse({
            'success': False,
            'error': 'Password is required.',
        }, status=400)

    try:
        result = DatabaseService.test_connection(
            host=host, port=port, db_name=db_name,
            username=username, password=password,
            ssl_mode=ssl_mode,
        )

        # Log the test (without password)
        AuditLog.log(
            action='DB_CONFIG_TESTED',
            module='system',
            user=request.user,
            new_data={
                'host': host,
                'port': port,
                'db_name': db_name,
                'username': username,
                'ssl_mode': ssl_mode,
                'result': 'success' if result['success'] else 'failed',
                'error': result.get('error', ''),
            },
            ip_address=client_ip(request),
        )

        return JsonResponse(result)

    except Exception as e:
        logger.exception('DB test failed')
        return JsonResponse({
            'success': False,
            'error': f'Test failed: {str(e)}',
        }, status=500)


# ─── APPLY NEW CONFIG ────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def db_apply_config(request):
    if not is_super_admin(request):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'},
            status=403
        )

    # Re-authentication required
    admin_password = request.POST.get('admin_password', '').strip()
    if not admin_password:
        return JsonResponse({
            'success': False,
            'error': 'Your password is required to apply changes.',
        }, status=400)

    user = authenticate(username=request.user.username, password=admin_password)
    if user is None or user.pk != request.user.pk:
        return JsonResponse({
            'success': False,
            'error': 'Invalid password.',
        }, status=403)

    confirm = request.POST.get('confirm', '').strip()
    if confirm != 'APPLY':
        return JsonResponse({
            'success': False,
            'error': 'Type "APPLY" exactly to confirm.',
        }, status=400)

    host     = request.POST.get('host', '').strip()
    port     = request.POST.get('port', '5432').strip()
    db_name  = request.POST.get('db_name', '').strip()
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '').strip()
    ssl_mode = request.POST.get('ssl_mode', 'prefer').strip()

    use_existing_pw = request.POST.get('use_existing_password') == '1'
    if use_existing_pw:
        current_config = DatabaseConfig.objects.filter(is_active=True).first()
        if current_config:
            password = current_config.get_password()

    if not all([host, port, db_name, username, password]):
        return JsonResponse({
            'success': False,
            'error': 'All fields are required.',
        }, status=400)

    # STEP 1: Test new connection first
    test_result = DatabaseService.test_connection(
        host=host, port=port, db_name=db_name,
        username=username, password=password,
        ssl_mode=ssl_mode,
    )

    if not test_result['success']:
        return JsonResponse({
            'success': False,
            'error': f'New connection test failed: {test_result["error"]}',
        }, status=400)

    # STEP 2: Create automatic backup of CURRENT database
    try:
        from apps.backups.services import BackupService
        from apps.backups.models import BackupRecord
        backup_service = BackupService(user=request.user)
        try:
            safety_backup = backup_service.create_sql_backup(
                trigger=BackupRecord.TRIGGER_PRE_UPGRADE
            )
            backup_msg = f'Safety backup created: {safety_backup.file_name}'
        except Exception as e:
            # Continue anyway but warn
            backup_msg = f'⚠ Backup failed but continuing: {e}'
            logger.warning(backup_msg)
    except Exception:
        backup_msg = 'Backup service not available.'

    # STEP 3: Save config to DB (with encryption)
    try:
        with transaction.atomic():
            # Mark current as last_known_good
            DatabaseConfig.objects.filter(is_active=True).update(
                is_active=False,
                is_last_known_good=True,
            )

            # Create new config
            new_config = DatabaseConfig(
                engine='django.db.backends.postgresql',
                host=host,
                port=port,
                db_name=db_name,
                username=username,
                ssl_mode=ssl_mode,
                is_active=True,
                tested_at=timezone.now(),
                test_result='success',
                applied_at=timezone.now(),
                applied_by=request.user,
            )
            new_config.set_password(password)
            new_config.save()

            # Update .env file
            DatabaseService.update_env_file(new_config.to_env_dict())

            # Log (WITHOUT password)
            AuditLog.log(
                action='DB_CONFIG_APPLIED',
                module='system',
                user=request.user,
                object_type='DatabaseConfig',
                object_id=new_config.pk,
                object_repr=f'{username}@{host}:{port}/{db_name}',
                new_data={
                    'host': host,
                    'port': port,
                    'db_name': db_name,
                    'username': username,
                    'ssl_mode': ssl_mode,
                    'server_version': test_result.get('server_version', ''),
                    'safety_backup': backup_msg,
                },
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': (
                'Database configuration applied. '
                'RESTART THE SERVER for changes to take effect.'
            ),
            'safety_backup': backup_msg,
            'requires_restart': True,
        })
    except Exception as e:
        logger.exception('DB config apply failed')
        return JsonResponse({
            'success': False,
            'error': f'Failed to apply: {str(e)}',
        }, status=500)


# ─── ROLLBACK ────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def db_rollback(request):
    if not is_super_admin(request):
        return JsonResponse(
            {'success': False, 'error': 'Permission denied.'},
            status=403
        )

    admin_password = request.POST.get('admin_password', '').strip()
    user = authenticate(username=request.user.username, password=admin_password)
    if user is None or user.pk != request.user.pk:
        return JsonResponse({
            'success': False,
            'error': 'Invalid password.',
        }, status=403)

    last_good = DatabaseConfig.objects.filter(is_last_known_good=True).first()
    if not last_good:
        return JsonResponse({
            'success': False,
            'error': 'No last-known-good configuration available.',
        }, status=400)

    try:
        with transaction.atomic():
            DatabaseConfig.objects.filter(is_active=True).update(is_active=False)
            last_good.is_active = True
            last_good.is_last_known_good = False
            last_good.save()

            DatabaseService.update_env_file(last_good.to_env_dict())

            AuditLog.log(
                action='DB_CONFIG_ROLLBACK',
                module='system',
                user=request.user,
                object_type='DatabaseConfig',
                object_id=last_good.pk,
                object_repr=str(last_good),
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': 'Rolled back to last-known-good config. RESTART THE SERVER.',
        })
    except Exception as e:
        logger.exception('DB rollback failed')
        return JsonResponse({
            'success': False,
            'error': str(e),
        }, status=500)