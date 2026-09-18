from django.urls import path
from . import views

urlpatterns = [
    path('',                    views.membership_list,       name='membership_list'),
    path('create/',             views.membership_create_ajax, name='membership_create'),
    path('<int:pk>/',           views.membership_detail,     name='membership_detail'),
    path('plans/',              views.plan_list,             name='plan_list'),
    path('plans/create/',       views.plan_create_ajax,      name='plan_create'),
    path('plans/<int:pk>/delete/', views.plan_delete,        name='plan_delete'),
]