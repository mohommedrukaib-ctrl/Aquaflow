from django.urls import path
from . import views

urlpatterns = [
    path('',              views.reports_home,       name='reports_home'),
    path('sales/',        views.sales_report,       name='sales_report'),
    path('services/',     views.service_report,     name='service_report'),
    path('customers/',    views.customer_report,    name='customer_report'),
    path('vehicles/',     views.vehicle_report,     name='vehicle_report'),
    path('cashiers/',     views.cashier_report,     name='cashier_report'),
    path('payments/',     views.payment_report,     name='payment_report'),
    path('inventory/',    views.inventory_report,   name='inventory_report'),
    path('profit-loss/',  views.profit_loss_report, name='profit_loss_report'),
]