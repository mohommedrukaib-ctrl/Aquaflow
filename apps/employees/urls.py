"""
AquaFlow — Employees URLs (Enforced)
Powered by Quantum Axis
"""

from django.urls import path
from . import views
from apps.system.features import feature_required

urlpatterns = [
    path('',                        feature_required('employees')(views.employee_list),        name='employee_list'),
    path('create/',                 feature_required('employees')(views.employee_create),      name='employee_create'),
    path('search/',                 feature_required('employees')(views.employee_search_ajax), name='employee_search'),
    path('<int:pk>/',               feature_required('employees')(views.employee_detail),      name='employee_detail'),
    path('<int:pk>/edit-inline/',   feature_required('employees')(views.employee_inline_edit), name='employee_inline_edit'),
    path('<int:pk>/delete/',        feature_required('employees')(views.employee_delete),      name='employee_delete'),
    path('positions/search/',       feature_required('employees')(views.position_search_ajax), name='position_search'),
    path('positions/create/',       feature_required('employees')(views.position_create_ajax), name='position_create'),
]