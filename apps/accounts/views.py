"""
AquaFlow — Custom Authentication Views
Powered by Quantum Axis
"""

import logging
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .security_models import LoginAttempt, AccountLockout, SecurityConfig
from apps.system.models import AuditLog

logger = logging.getLogger('apps')


def client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ─── LOGIN VIEW ──────────────────────────────────────────────

# apps/accounts/views.py (Replace your login_view with this)

def login_view(request):
    """
    Custom login view with:
    - Rate limiting
    - Account lockout
    - Login attempt tracking
    - Role assignment check (NEW)
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        next_url = request.POST.get('next', '/dashboard/')

        if not username or not password:
            messages.error(request, 'Username and password required.')
            return render(request, 'accounts/login.html', {'next': next_url})

        try:
            config = SecurityConfig.get_config()
        except Exception:
            config = None

        # Check if too many recent failures from this IP
        if config:
            ip = client_ip(request)
            ip_failures = LoginAttempt.get_recent_failures(
                ip_address=ip,
                minutes=config.failed_attempt_window,
            )
            if ip_failures >= config.max_failed_attempts * 2:
                LoginAttempt.record(
                    username, request,
                    LoginAttempt.STATUS_LOCKED,
                    reason=f'IP blocked after {ip_failures} failed attempts',
                )
                messages.error(
                    request,
                    f'Too many failed attempts from your IP. '
                    f'Try again in {config.lockout_duration_minutes} minutes.'
                )
                return render(request, 'accounts/login.html', {'next': next_url})

        # Check user-specific lockout
        try:
            user_obj = User.objects.get(username=username)
            if AccountLockout.is_user_locked(user_obj):
                LoginAttempt.record(
                    username, request,
                    LoginAttempt.STATUS_LOCKED,
                    reason='Account currently locked',
                )
                messages.error(
                    request,
                    'Account is locked due to too many failed attempts. '
                    'Contact your administrator.'
                )
                return render(request, 'accounts/login.html', {'next': next_url})
        except User.DoesNotExist:
            pass

        # Try authenticate
        user = authenticate(request, username=username, password=password)

        if user is None:
            LoginAttempt.record(
                username, request,
                LoginAttempt.STATUS_FAILED,
                reason='Invalid credentials',
            )

            # Check if we should lock account
            if config:
                user_failures = LoginAttempt.get_recent_failures(
                    username=username,
                    minutes=config.failed_attempt_window,
                )
                if user_failures >= config.max_failed_attempts:
                    try:
                        user_to_lock = User.objects.get(username=username)
                        AccountLockout.lock_user(
                            user_to_lock,
                            minutes=config.lockout_duration_minutes,
                            reason=f'{user_failures} failed login attempts',
                        )

                        AuditLog.log(
                            action='ACCOUNT_LOCKED',
                            module='security',
                            user=user_to_lock,
                            object_type='User',
                            object_id=user_to_lock.pk,
                            object_repr=user_to_lock.username,
                            new_data={
                                'reason': f'{user_failures} failed attempts',
                                'unlock_in_minutes': config.lockout_duration_minutes,
                            },
                            ip_address=client_ip(request),
                        )
                        messages.error(
                            request,
                            f'Too many failed attempts. Account locked for '
                            f'{config.lockout_duration_minutes} minutes.'
                        )
                    except User.DoesNotExist:
                        messages.error(request, 'Invalid username or password.')
                else:
                    remaining = config.max_failed_attempts - user_failures
                    messages.error(
                        request,
                        f'Invalid username or password. '
                        f'{remaining} attempts remaining before lockout.'
                    )
            else:
                messages.error(request, 'Invalid username or password.')

            return render(request, 'accounts/login.html', {'next': next_url})

        # ─── NEW: Check if User is Assigned and Active ─────────────────────
        # Superusers bypass this check, everyone else must have an active profile and role
        if not user.is_superuser:
            has_valid_profile = hasattr(user, 'profile') and user.profile.role and user.profile.status == 'active'
            
            if not has_valid_profile:
                LoginAttempt.record(
                    username, request,
                    LoginAttempt.STATUS_FAILED,
                    reason='Account not assigned or inactive',
                )
                messages.error(
                    request, 
                    'Your account is not assigned to a role or is currently inactive. Please contact the administrator.'
                )
                return render(request, 'accounts/login.html', {'next': next_url})
        # ───────────────────────────────────────────────────────────────────

        # Success
        auth_login(request, user)

        LoginAttempt.record(
            username, request,
            LoginAttempt.STATUS_SUCCESS,
        )

        AuditLog.log(
            action='LOGIN_SUCCESS',
            module='security',
            user=user,
            object_type='User',
            object_id=user.pk,
            object_repr=user.username,
            ip_address=client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )

        # Set session timeout
        try:
            config = SecurityConfig.get_config()
            request.session.set_expiry(config.session_timeout_minutes * 60)
        except Exception:
            pass

        request.session['last_activity'] = timezone.now().isoformat()

        return redirect(next_url or 'dashboard')

    return render(request, 'accounts/login.html', {'next': request.GET.get('next', '')})

    
# ─── LOGOUT VIEW ─────────────────────────────────────────────

def logout_view(request):
    if request.user.is_authenticated:
        AuditLog.log(
            action='LOGOUT',
            module='security',
            user=request.user,
            object_type='User',
            object_id=request.user.pk,
            object_repr=request.user.username,
            ip_address=client_ip(request),
        )
        auth_logout(request)
        messages.info(request, 'You have been logged out.')

    return redirect('login')


# ─── CHANGE PASSWORD ─────────────────────────────────────────

@login_required
@require_http_methods(['GET', 'POST'])
def change_password(request):
    if request.method == 'POST':
        current = request.POST.get('current_password', '').strip()
        new1    = request.POST.get('new_password', '').strip()
        new2    = request.POST.get('new_password_confirm', '').strip()

        # Verify current
        user = authenticate(username=request.user.username, password=current)
        if user is None:
            messages.error(request, 'Current password is incorrect.')
            return render(request, 'accounts/change_password.html')

        if new1 != new2:
            messages.error(request, 'New passwords do not match.')
            return render(request, 'accounts/change_password.html')

        # Validate strength
        try:
            config = SecurityConfig.get_config()
        except Exception:
            config = None

        errors = validate_password_strength(new1, config)
        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'accounts/change_password.html')

        # Set new
        request.user.set_password(new1)
        request.user.save()

        # Re-auth to prevent logout
        user = authenticate(username=request.user.username, password=new1)
        if user:
            auth_login(request, user)

        AuditLog.log(
            action='PASSWORD_CHANGED',
            module='security',
            user=request.user,
            object_type='User',
            object_id=request.user.pk,
            object_repr=request.user.username,
            ip_address=client_ip(request),
        )

        messages.success(request, 'Password changed successfully.')
        return redirect('dashboard')

    return render(request, 'accounts/change_password.html')


def validate_password_strength(password, config):
    """Return list of error messages, or empty list if valid."""
    errors = []

    if not config:
        min_len = 8
        require_upper = True
        require_num = True
        require_special = False
    else:
        min_len = config.min_password_length
        require_upper = config.require_uppercase
        require_num = config.require_number
        require_special = config.require_special_char

    if len(password) < min_len:
        errors.append(f'Password must be at least {min_len} characters.')

    if require_upper and not any(c.isupper() for c in password):
        errors.append('Password must contain at least one uppercase letter.')

    if require_num and not any(c.isdigit() for c in password):
        errors.append('Password must contain at least one number.')

    if require_special:
        specials = '!@#$%^&*()_+-=[]{}|;:,.<>?/'
        if not any(c in specials for c in password):
            errors.append('Password must contain at least one special character.')

    return errors


# ─── SECURITY DASHBOARD (Super Admin) ────────────────────────

@login_required
def security_dashboard(request):
    from apps.accounts.models import RoleCode
    try:
        is_super = request.user.profile.role.code == RoleCode.SUPER_ADMIN
    except Exception:
        is_super = False

    if not is_super:
        messages.error(request, 'Only Super Admin can view security dashboard.')
        return redirect('dashboard')

    from django.db.models import Count
    from datetime import timedelta

    config = SecurityConfig.get_config()
    now = timezone.now()
    today = now.date()

    # Recent stats
    login_stats = LoginAttempt.objects.filter(
        timestamp__gte=now - timedelta(days=7),
    ).values('status').annotate(count=Count('id'))

    stats = {'success': 0, 'failed': 0, 'locked': 0}
    for s in login_stats:
        stats[s['status']] = s['count']

    # Currently locked accounts
    locked_accounts = AccountLockout.objects.filter(
        unlocked_at__isnull=True,
        unlock_at__gt=now,
    ).select_related('user')

    # Recent failed logins (last 24h)
    recent_failures = LoginAttempt.objects.filter(
        status=LoginAttempt.STATUS_FAILED,
        timestamp__gte=now - timedelta(hours=24),
    ).order_by('-timestamp')[:20]

    # Recent successful logins
    recent_successes = LoginAttempt.objects.filter(
        status=LoginAttempt.STATUS_SUCCESS,
        timestamp__gte=now - timedelta(hours=24),
    ).order_by('-timestamp')[:10]

    context = {
        'page_title': 'Security Dashboard',
        'config':     config,
        'stats':      stats,
        'locked_accounts':  locked_accounts,
        'recent_failures':  recent_failures,
        'recent_successes': recent_successes,
    }
    return render(request, 'accounts/security_dashboard.html', context)


@login_required
@require_http_methods(['POST'])
def unlock_account(request, user_id):
    from apps.accounts.models import RoleCode
    try:
        is_super = request.user.profile.role.code == RoleCode.SUPER_ADMIN
    except Exception:
        is_super = False

    if not is_super:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    try:
        user = User.objects.get(pk=user_id)
        lockout = AccountLockout.objects.filter(user=user).first()
        if lockout:
            lockout.unlocked_at = timezone.now()
            lockout.unlocked_by = request.user
            lockout.save()

            AuditLog.log(
                action='ACCOUNT_UNLOCKED',
                module='security',
                user=request.user,
                object_type='User',
                object_id=user.pk,
                object_repr=user.username,
                ip_address=client_ip(request),
            )

        return JsonResponse({
            'success': True,
            'message': f'Account "{user.username}" unlocked.',
        })
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found.'}, status=404)


@login_required
@require_http_methods(['POST'])
def security_config_save(request):
    from apps.accounts.models import RoleCode
    try:
        is_super = request.user.profile.role.code == RoleCode.SUPER_ADMIN
    except Exception:
        is_super = False

    if not is_super:
        return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)

    try:
        config = SecurityConfig.get_config()
        config.max_failed_attempts = int(request.POST.get('max_failed_attempts', 5))
        config.lockout_duration_minutes = int(request.POST.get('lockout_duration_minutes', 30))
        config.failed_attempt_window = int(request.POST.get('failed_attempt_window', 15))
        config.session_timeout_minutes = int(request.POST.get('session_timeout_minutes', 480))
        config.idle_timeout_minutes = int(request.POST.get('idle_timeout_minutes', 60))
        config.min_password_length = int(request.POST.get('min_password_length', 8))
        config.require_uppercase = request.POST.get('require_uppercase') == 'true'
        config.require_number = request.POST.get('require_number') == 'true'
        config.require_special_char = request.POST.get('require_special_char') == 'true'
        config.password_expiry_days = int(request.POST.get('password_expiry_days', 0))
        config.force_https = request.POST.get('force_https') == 'true'
        config.save()

        AuditLog.log(
            action='SECURITY_CONFIG_UPDATED',
            module='security',
            user=request.user,
            ip_address=client_ip(request),
        )

        return JsonResponse({'success': True, 'message': 'Security settings saved.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)