from django.urls import path
from . import views

urlpatterns = [
    path('',                    views.loyalty_dashboard,       name='loyalty_dashboard'),
    path('config/',             views.loyalty_config_update,   name='loyalty_config'),
    path('customer/<int:customer_id>/', views.customer_loyalty_history, name='customer_loyalty_history'),
    path('customer/<int:customer_id>/adjust/', views.points_adjust, name='points_adjust'),
]