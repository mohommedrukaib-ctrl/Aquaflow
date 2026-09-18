from django.urls import path
from . import views

urlpatterns = [
    path('',                             views.trash_list,    name='trash_list'),
    path('<str:item_type>/<int:pk>/restore/', views.restore_item, name='restore_item'),
    path('<str:item_type>/<int:pk>/purge/',   views.purge_item,   name='purge_item'),
]