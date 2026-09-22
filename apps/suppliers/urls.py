"""
AquaFlow — Suppliers URLs (Feature-Enforced)
Powered by Quantum Axis

inventory flag   → suppliers
purchase_orders  → purchases
"""

from django.urls import path
from . import views
from apps.system.features import feature_required

urlpatterns = [
    # ─── Suppliers (inventory feature) ─────────────────────
    path('',                              feature_required('inventory')(views.supplier_list),        name='supplier_list'),
    path('search/',                       views.supplier_search_ajax, name='supplier_search'),
    path('create/',                       feature_required('inventory')(views.supplier_create_ajax), name='supplier_create_ajax'),
    path('<int:pk>/',                     feature_required('inventory')(views.supplier_detail),      name='supplier_detail'),
    path('<int:pk>/edit-inline/',         feature_required('inventory')(views.supplier_inline_edit), name='supplier_inline_edit'),
    path('<int:pk>/delete/',              feature_required('inventory')(views.supplier_delete),      name='supplier_delete'),

    # ─── Purchases (purchase_orders feature) ───────────────
    path('purchases/',                    feature_required('purchase_orders')(views.purchase_list),        name='purchase_list'),
    path('purchases/new/',                feature_required('purchase_orders')(views.purchase_create),      name='purchase_create'),
    path('purchases/<int:pk>/',           feature_required('purchase_orders')(views.purchase_detail),      name='purchase_detail'),
    path('purchases/<int:pk>/pay/',       feature_required('purchase_orders')(views.purchase_add_payment), name='purchase_add_payment'),
]