from django.urls import path
from . import views

urlpatterns = [
    path('',           views.booking_list,   name='booking_list'),
    path('add/',       views.booking_create, name='booking_create'),
    path('search/',    views.booking_search_ajax, name='booking_search_ajax'),
    path('<int:pk>/',       views.booking_detail, name='booking_detail'),
    path('<int:pk>/edit/',  views.booking_edit,   name='booking_edit'),
    path('<int:pk>/status/',views.booking_status_update, name='booking_status_update'),

    # ─── SmartInput AJAX ────────────────────────────────────
    path('services/search/',   views.service_search_ajax,  name='booking_service_search'),
    path('services/create/',   views.service_create_ajax,  name='booking_service_create'),
    path('branches/search/',   views.branch_search_ajax,   name='booking_branch_search'),
    path('employees/search/',  views.employee_search_ajax, name='booking_employee_search'),
    path('bays/search/',       views.wash_bay_search_ajax, name='booking_wash_bay_search'),
    path('bays/create/',       views.wash_bay_create_ajax, name='booking_wash_bay_create'),

    path('customer-vehicles/', views.customer_vehicles_ajax, name='booking_customer_vehicles'),
    path('vehicle-details/<int:pk>/', views.vehicle_full_details_ajax, name='booking_vehicle_details'),

    path('vehicles/quick-create/',
     views.vehicle_quick_create_ajax,
     name='booking_vehicle_quick_create'),  
]