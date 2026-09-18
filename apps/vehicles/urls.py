"""
AquaFlow — Vehicle URLs
Powered by Quantum Axis
"""

from django.urls import path
from . import views

urlpatterns = [

    # ─── Vehicles ─────────────────────────────────────────────
    path('',                        views.vehicle_list,   name='vehicle_list'),
    path('add/',                    views.vehicle_create, name='vehicle_create'),
    path('<int:pk>/',               views.vehicle_detail, name='vehicle_detail'),
    path('<int:pk>/edit/',          views.vehicle_edit,   name='vehicle_edit'),
    path('<int:pk>/delete/',        views.vehicle_delete, name='vehicle_delete'),

    # ─── Brands ───────────────────────────────────────────────
    path('brands/',                 views.brand_list,          name='brand_list'),
    path('brands/create/',          views.brand_create_ajax,   name='brand_create_ajax'),
    path('brands/search/',          views.brand_search_ajax,   name='brand_search_ajax'),

    # ─── Models ───────────────────────────────────────────────
    path('models/create/',          views.model_create_ajax,   name='model_create_ajax'),
    path('models/search/',          views.model_search_ajax,   name='model_search_ajax'),
    path('models/by-brand/',        views.models_by_brand,     name='models_by_brand'),

    # ─── Master Data (Smart Input) ────────────────────────────
    path('types/search/',           views.vehicle_type_search_ajax,  name='vehicle_type_search'),
    path('types/create/',           views.vehicle_type_create_ajax,  name='vehicle_type_create'),
    path('colors/search/',          views.color_search_ajax,         name='color_search'),
    path('colors/create/',          views.color_create_ajax,         name='color_create'),
    path('fuels/search/',           views.fuel_type_search_ajax,     name='fuel_search'),
    path('fuels/create/',           views.fuel_type_create_ajax,     name='fuel_create'),

    # ─── Customer Quick Create ────────────────────────────────
    path('customers/quick-create/', views.customer_quick_create_ajax, name='vehicle_customer_quick_create'),

    # ─── Vehicle Search ───────────────────────────────────────
    path('search/',                 views.vehicle_search_ajax,       name='vehicle_search_ajax'),

    path('registration-check/',
     views.vehicle_registration_check,
     name='vehicle_registration_check'),
]