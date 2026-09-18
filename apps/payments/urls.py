from django.urls import path
from . import views

urlpatterns = [
    path('',                  views.payment_list,   name='payment_list'),
    path('summary/',          views.sales_summary,  name='sales_summary'),
    path('refund/<int:invoice_id>/', views.process_refund, name='process_refund'),
]