"""
AquaFlow REST API Root
Powered by Quantum Axis
"""

from django.urls import path
from django.http import JsonResponse
from django.conf import settings


def api_root(request):
    return JsonResponse({
        'system':    settings.AQUAFLOW_SYSTEM_NAME,
        'developer': settings.AQUAFLOW_DEVELOPER,
        'version':   settings.AQUAFLOW_VERSION,
        'status':    'operational',
        'currency':  settings.DEFAULT_CURRENCY_CODE,
        'timezone':  settings.TIME_ZONE,
    })


urlpatterns = [
    path('', api_root, name='api-root'),
]