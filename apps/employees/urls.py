from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.employee_list,        name='employee_list'),
    path('create/',                 views.employee_create,      name='employee_create'),
    path('search/',                 views.employee_search_ajax, name='employee_search'),
    path('<int:pk>/',               views.employee_detail,      name='employee_detail'),
    path('<int:pk>/edit-inline/',   views.employee_inline_edit, name='employee_inline_edit'),
    path('<int:pk>/delete/',        views.employee_delete,      name='employee_delete'),
    path('positions/search/',       views.position_search_ajax, name='position_search'),
    path('positions/create/',       views.position_create_ajax, name='position_create'),
]