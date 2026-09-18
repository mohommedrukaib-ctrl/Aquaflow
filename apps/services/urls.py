from django.urls import path
from . import views

urlpatterns = [
    path('',                          views.service_list,           name='service_list'),
    path('add/',                      views.service_create,         name='service_create'),
    path('search/',                   views.service_search_ajax,    name='service_search_ajax'),
    path('categories/',               views.category_list,          name='service_category_list'),
    path('categories/create/',        views.category_create_ajax,   name='service_category_create'),
    path('<int:pk>/',                 views.service_detail,         name='service_detail'),
    path('<int:pk>/edit/',            views.service_edit,           name='service_edit'),
    path('<int:pk>/delete/',          views.service_delete,         name='service_delete'),
    path('<int:pk>/edit-inline/',     views.service_inline_edit,    name='service_inline_edit'),
    path('<int:pk>/prices/add/',      views.service_price_add,      name='service_price_add'),
    path('<int:pk>/quick-price/',     views.service_quick_price_ajax, name='service_quick_price'),
    path('<int:pk>/prices/<int:price_pk>/delete/', views.service_price_delete, name='service_price_delete'),
]