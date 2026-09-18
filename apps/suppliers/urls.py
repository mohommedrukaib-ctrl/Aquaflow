from django.urls import path
from . import views

urlpatterns = [
    # Suppliers
    path('',                              views.supplier_list,        name='supplier_list'),
    path('search/',                       views.supplier_search_ajax, name='supplier_search'),
    path('create/',                       views.supplier_create_ajax, name='supplier_create_ajax'),
    path('<int:pk>/',                     views.supplier_detail,      name='supplier_detail'),
    path('<int:pk>/edit-inline/',         views.supplier_inline_edit, name='supplier_inline_edit'),
    path('<int:pk>/delete/',              views.supplier_delete,      name='supplier_delete'),

    # Purchases
    path('purchases/',                    views.purchase_list,        name='purchase_list'),
    path('purchases/new/',                views.purchase_create,      name='purchase_create'),
    path('purchases/<int:pk>/',           views.purchase_detail,      name='purchase_detail'),
    path('purchases/<int:pk>/pay/',       views.purchase_add_payment, name='purchase_add_payment'),
]