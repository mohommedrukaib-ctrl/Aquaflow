"""
AquaFlow — Inventory URLs (Enforced)
Powered by Quantum Axis
"""

from django.urls import path
from . import views
from apps.system.features import feature_required

urlpatterns = [
    path('',                              feature_required('inventory')(views.product_list),         name='product_list'),
    path('movements/',                    feature_required('inventory')(views.stock_movements),      name='stock_movements'),
    path('products/create/',              feature_required('inventory')(views.product_create_ajax),  name='product_create_ajax'),
    path('products/<int:pk>/',            feature_required('inventory')(views.product_detail),       name='product_detail'),
    path('products/<int:pk>/edit-inline/',feature_required('inventory')(views.product_inline_edit),  name='product_inline_edit'),
    path('products/<int:pk>/delete/',     feature_required('inventory')(views.product_delete),       name='product_delete'),
    path('products/<int:pk>/adjust/',     feature_required('inventory')(views.stock_adjust),         name='stock_adjust'),
    path('products/<int:pk>/stock-in/',   feature_required('inventory')(views.stock_in),             name='stock_in'),
]