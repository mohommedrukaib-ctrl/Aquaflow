from django.urls import path
from . import views

urlpatterns = [
    path('',            views.audit_dashboard,   name='audit_dashboard'),
    path('logs/',       views.audit_list,        name='audit_list'),
    path('logs/<int:pk>/', views.audit_detail,   name='audit_detail'),
    path('logs/export/', views.audit_export_csv, name='audit_export_csv'),
]