from django.urls import path
from . import views

urlpatterns = [
    path('',                    views.order_list,   name='order_list'),
    path('<int:pk>/',           views.order_detail, name='order_detail'),
    path('<int:pk>/void/',      views.order_void,   name='order_void'),
]