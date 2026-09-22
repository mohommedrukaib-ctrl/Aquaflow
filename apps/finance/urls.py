"""
AquaFlow — Finance URLs (Enforced)
Powered by Quantum Axis
"""

from django.urls import path
from . import views
from apps.system.features import feature_required

urlpatterns = [
    path('',                    feature_required('finance')(views.expense_list),          name='expense_list'),
    path('create/',             feature_required('finance')(views.expense_create_ajax),   name='expense_create_ajax'),
    path('<int:pk>/delete/',    feature_required('finance')(views.expense_delete),        name='expense_delete'),
    path('categories/search/',  feature_required('finance')(views.category_search_ajax),  name='expense_category_search'),
    path('categories/create/',  feature_required('finance')(views.category_create_ajax),  name='expense_category_create'),
]