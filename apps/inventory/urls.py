from django.urls import path
from . import views

urlpatterns = [
    path('',                              views.product_list,         name='product_list'),
    path('movements/',                    views.stock_movements,      name='stock_movements'),
    path('products/create/',              views.product_create_ajax,  name='product_create_ajax'),
    path('products/<int:pk>/',            views.product_detail,       name='product_detail'),
    path('products/<int:pk>/edit-inline/',views.product_inline_edit,  name='product_inline_edit'),
    path('products/<int:pk>/delete/',     views.product_delete,       name='product_delete'),
    path('products/<int:pk>/adjust/',     views.stock_adjust,         name='stock_adjust'),
    path('products/<int:pk>/stock-in/',   views.stock_in,             name='stock_in'),
]