"""
AquaFlow — System Health Views
Powered by Quantum Axis
"""

import os
import shutil
import platform
import logging
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.accounts.models import RoleCode

logger = logging.getLogger('apps')


def is_super_admin(request):
    try:
        return request.user.profile.role.code == RoleCode.SUPER_ADMIN
    except Exception:
        return False


@login_required
def system_health(request):
    if not is_super_admin(request):
        messages.error(request, 'Only Super Admin can view system health.')
        return redirect('dashboard')

    health = {}

    # Database check
    db_status = 'error'
    db_version = ''
    db_size = 0
    db_error = ''
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT version()')
            db_version = cursor.fetchone()[0].split(',')[0]

            cursor.execute("SELECT pg_database_size(current_database())")
            db_size = cursor.fetchone()[0]

        db_status = 'ok'
    except Exception as e:
        db_error = str(e)

    health['database'] = {
        'status':   db_status,
        'version':  db_version,
        'size_mb':  db_size / (1024 * 1024) if db_size else 0,
        'host':     settings.DATABASES['default'].get('HOST', ''),
        'name':     settings.DATABASES['default'].get('NAME', ''),
        'error':    db_error,
    }

    # Backup check
    try:
        from apps.backups.models import BackupRecord
        from apps.backups.services import BackupService

        last_backup = BackupRecord.objects.filter(
            status=BackupRecord.STATUS_SUCCESS,
        ).order_by('-started_at').first()

        pg_info = BackupService.get_system_info()

        health['backups'] = {
            'status': 'ok' if last_backup else 'warning',
            'last_backup': last_backup.started_at if last_backup else None,
            'last_backup_name': last_backup.file_name if last_backup else None,
            'total_backups': BackupRecord.objects.count(),
            'pg_dump_available': pg_info['sql_available'],
        }
    except Exception as e:
        health['backups'] = {'status': 'error', 'error': str(e)}

    # Disk space
    try:
        base_path = Path(settings.BASE_DIR)
        total, used, free = shutil.disk_usage(str(base_path))
        health['disk'] = {
            'status':      'ok' if (free / total * 100) > 10 else 'warning',
            'total_gb':    total / (1024**3),
            'used_gb':     used / (1024**3),
            'free_gb':     free / (1024**3),
            'used_percent': (used / total * 100),
        }
    except Exception as e:
        health['disk'] = {'status': 'error', 'error': str(e)}

    # Migrations check
    try:
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)

        health['migrations'] = {
            'status':   'ok' if not plan else 'warning',
            'pending':  len(plan),
            'message':  'All migrations applied' if not plan else f'{len(plan)} pending migrations',
        }
    except Exception as e:
        health['migrations'] = {'status': 'error', 'error': str(e)}

    # Cache
    try:
        from django.core.cache import cache
        cache.set('_health_check', 'ok', 10)
        val = cache.get('_health_check')
        health['cache'] = {
            'status':  'ok' if val == 'ok' else 'error',
            'backend': settings.CACHES['default']['BACKEND'],
        }
    except Exception as e:
        health['cache'] = {'status': 'error', 'error': str(e)}

    # System info
    health['system'] = {
        'platform':     platform.system(),
        'platform_ver': platform.release(),
        'python':       platform.python_version(),
        'django':       __import__('django').get_version(),
        'debug_mode':   settings.DEBUG,
        'timezone':     str(settings.TIME_ZONE),
    }

    # Overall status
    statuses = [h.get('status') for h in health.values() if isinstance(h, dict)]
    if 'error' in statuses:
        overall = 'error'
    elif 'warning' in statuses:
        overall = 'warning'
    else:
        overall = 'ok'

    context = {
        'page_title': 'System Health',
        'health':     health,
        'overall':    overall,
        'checked_at': timezone.now(),
    }
    return render(request, 'system/health.html', context)