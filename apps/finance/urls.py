from django.urls import path
from . import views

urlpatterns = [
    path('',                    views.expense_list,          name='expense_list'),
    path('create/',             views.expense_create_ajax,   name='expense_create_ajax'),
    path('<int:pk>/delete/',    views.expense_delete,        name='expense_delete'),
    path('categories/search/',  views.category_search_ajax,  name='expense_category_search'),
    path('categories/create/',  views.category_create_ajax,  name='expense_category_create'),
]