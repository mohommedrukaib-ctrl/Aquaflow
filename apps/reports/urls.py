"""
AquaFlow — Reports URLs (Enforced)
Powered by Quantum Axis
"""

from django.urls import path
from . import views
from apps.system.features import feature_required

urlpatterns = [
    path('',                  feature_required('reports')(views.reports_home),       name='reports_home'),
    path('sales/',        feature_required('reports')(views.sales_report),       name='sales_report'),
    path('services/',     feature_required('reports')(views.service_report),     name='service_report'),
    path('customers/',    feature_required('reports')(views.customer_report),    name='customer_report'),
    path('vehicles/',     feature_required('reports')(views.vehicle_report),     name='vehicle_report'),
    path('cashiers/',     feature_required('reports')(views.cashier_report),     name='cashier_report'),
    path('payments/',     feature_required('reports')(views.payment_report),     name='payment_report'),
    path('inventory/',    feature_required('reports')(views.inventory_report),   name='inventory_report'),
    path('profit-loss/',  feature_required('reports')(views.profit_loss_report), name='profit_loss_report'),
]