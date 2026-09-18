"""
AquaFlow — Customer URLs
Powered by Quantum Axis
"""

from django.urls import path
from . import views

urlpatterns = [
    path('',
         views.customer_list,
         name='customer_list'),

    path('add/',
         views.customer_create,
         name='customer_create'),

    path('<int:pk>/',
         views.customer_detail,
         name='customer_detail'),

    path('<int:pk>/edit/',
         views.customer_edit,
         name='customer_edit'),

    path('<int:pk>/delete/',
         views.customer_delete,
         name='customer_delete'),

    # AJAX endpoints
    path('search/',
         views.customer_search_ajax,
         name='customer_search_ajax'),

    path('phone-lookup/',
         views.customer_phone_lookup,
         name='customer_phone_lookup'),
]