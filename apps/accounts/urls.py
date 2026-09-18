"""
AquaFlow — Accounts URLs
Powered by Quantum Axis
"""

from django.urls import path
from . import views
from . import role_views

urlpatterns = [
    # Auth
    path('login/',           views.login_view,         name='login'),
    path('logout/',          views.logout_view,        name='logout'),
    path('change-password/', views.change_password,    name='change_password'),

    # Security
    path('security/',        views.security_dashboard, name='security_dashboard'),
    path('security/unlock/<int:user_id>/', views.unlock_account, name='unlock_account'),
    path('security/config/', views.security_config_save, name='security_config_save'),

    # Roles
    path('roles/',                    role_views.role_list,   name='role_list'),
    path('roles/create/',             role_views.role_create, name='role_create'),
    path('roles/<int:pk>/edit/',      role_views.role_edit,   name='role_edit'),
    path('roles/<int:pk>/update/',    role_views.role_update, name='role_update'),
    path('roles/<int:pk>/delete/',    role_views.role_delete, name='role_delete'),

    # Users
    path('users/',                       role_views.user_list,           name='user_list'),
    path('users/create/',                role_views.user_create,         name='user_create'),
    path('users/<int:user_id>/role/',    role_views.user_change_role,    name='user_change_role'),
    path('users/<int:user_id>/toggle/',  role_views.user_toggle_active,  name='user_toggle_active'),
    path('users/<int:user_id>/reset/',   role_views.user_reset_password, name='user_reset_password'),
]