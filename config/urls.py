"""
AquaFlow URL Configuration
Powered by Quantum Axis
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [

    # Django admin (internal only)
    path('django-admin/', admin.site.urls),

    # Root → Dashboard
    path(
        '',
        RedirectView.as_view(url='/dashboard/', permanent=False),
        name='root'
    ),

    # ─── Authentication ───────────────────────────────────────
    path('accounts/', include('apps.accounts.urls')),

    # ─── Main Application ─────────────────────────────────────
    path('dashboard/', include('apps.system.urls.dashboard')),
    path('customers/', include('apps.customers.urls')),
    path('vehicles/', include('apps.vehicles.urls')),
    path('services/', include('apps.services.urls')),
    path('bookings/', include('apps.bookings.urls')),
    path('pos/', include('apps.pos.urls')),
    path('orders/', include('apps.orders.urls')),
    path('invoices/', include('apps.invoices.urls')),
    path('payments/', include('apps.payments.urls')),
    path('wash/', include('apps.wash.urls')),
    path('employees/', include('apps.employees.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('suppliers/', include('apps.suppliers.urls')),
    path('finance/', include('apps.finance.urls')),
    path('memberships/', include('apps.memberships.urls')),
    path('reports/', include('apps.reports.urls')),
    path('system/', include('apps.system.urls.system')),
    path('system/trash/', include('apps.trash.urls')),
    path('system/audit/', include('apps.audit.urls')),
    path('system/backups/', include('apps.backups.urls')),
    path('loyalty/', include('apps.loyalty.urls')),

    path('business/', include('apps.businesses.urls')),
    # ─── REST API ─────────────────────────────────────────────
    path('api/v1/', include('apps.system.urls.api')),

]

# ─── Debug Toolbar ────────────────────────────────────────────
if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# ─── Media Files (Development) ────────────────────────────────
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )