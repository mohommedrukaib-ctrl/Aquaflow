"""
AquaFlow — Loyalty URLs (Enforced)
Powered by Quantum Axis
"""

from django.urls import path
from . import views
from apps.system.features import feature_required

urlpatterns = [
    path('',                    feature_required('loyalty')(views.loyalty_dashboard),       name='loyalty_dashboard'),
    path('config/',             feature_required('loyalty')(views.loyalty_config_update),   name='loyalty_config'),
    path('customer/<int:customer_id>/', feature_required('loyalty')(views.customer_loyalty_history), name='customer_loyalty_history'),
    path('customer/<int:customer_id>/adjust/', feature_required('loyalty')(views.points_adjust), name='points_adjust'),
]