"""
AquaFlow System URLs
Powered by Quantum Axis
"""

from django.urls import path
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.system import db_views
from apps.system import health_views
from apps.system import qa_views
from apps.system import features_views


@login_required
def system_home(request):
    context = {
        'page_title': 'System Settings',
    }
    return render(request, 'system/system.html', context)


urlpatterns = [
    path('',                     system_home,                       name='system'),
    path('health/',              health_views.system_health,        name='system_health'),
    path('qa/',                  qa_views.qa_dashboard,             name='qa_dashboard'),
    path('qa/json/',             qa_views.qa_json,                  name='qa_json'),
    path('database/',            db_views.db_config_page,           name='db_config_page'),
    path('database/test/',       db_views.db_test_connection,       name='db_test'),
    path('database/apply/',      db_views.db_apply_config,          name='db_apply'),
    path('database/rollback/',   db_views.db_rollback,              name='db_rollback'),

    # ─── Feature Flags ──────────────────────────────────────
    path('features/',            features_views.manage_features,     name='manage_features'),
    path('features/toggle/',     features_views.toggle_feature_ajax, name='toggle_feature_ajax'),
    path('features/bulk/',       features_views.bulk_toggle_features, name='bulk_toggle_features'),
]