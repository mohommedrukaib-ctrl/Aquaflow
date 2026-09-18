"""
AquaFlow — QA / Diagnostics Views
Powered by Quantum Axis
"""

import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import JsonResponse

from apps.accounts.models import RoleCode
from .qa_service import QAService

logger = logging.getLogger('apps')


def is_super_admin(request):
    try:
        return request.user.profile.role.code == RoleCode.SUPER_ADMIN
    except Exception:
        return False


@login_required
def qa_dashboard(request):
    """System QA / Diagnostics dashboard."""
    if not is_super_admin(request):
        messages.error(request, 'Only Super Admin can view QA dashboard.')
        return redirect('dashboard')

    qa = QAService()
    report = qa.run_all()

    # Group by category
    grouped = {}
    for r in report['results']:
        cat = r['category']
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(r)

    # Overall status
    if report['errors'] > 0:
        overall = 'error'
        overall_label = 'CRITICAL ISSUES FOUND'
    elif report['warnings'] > 0:
        overall = 'warning'
        overall_label = 'Warnings Present'
    else:
        overall = 'pass'
        overall_label = 'ALL CHECKS PASSED'

    context = {
        'page_title':    'System QA & Diagnostics',
        'report':        report,
        'grouped':       grouped,
        'overall':       overall,
        'overall_label': overall_label,
    }
    return render(request, 'system/qa.html', context)


@login_required
def qa_json(request):
    """Return QA report as JSON."""
    if not is_super_admin(request):
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    qa = QAService()
    report = qa.run_all()

    return JsonResponse({
        'passed':   report['passed'],
        'warnings': report['warnings'],
        'errors':   report['errors'],
        'total':    report['total'],
        'results':  report['results'],
    })