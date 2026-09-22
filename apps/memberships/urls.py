"""
AquaFlow — Memberships URLs (Enforced)
Powered by Quantum Axis
"""

from django.urls import path
from . import views
from apps.system.features import feature_required

urlpatterns = [
    path('',                    feature_required('memberships')(views.membership_list),       name='membership_list'),
    path('create/',             feature_required('memberships')(views.membership_create_ajax), name='membership_create'),
    path('<int:pk>/',           feature_required('memberships')(views.membership_detail),     name='membership_detail'),
    path('plans/',              feature_required('memberships')(views.plan_list),             name='plan_list'),
    path('plans/create/',       feature_required('memberships')(views.plan_create_ajax),      name='plan_create'),
    path('plans/<int:pk>/delete/', feature_required('memberships')(views.plan_delete),        name='plan_delete'),
]