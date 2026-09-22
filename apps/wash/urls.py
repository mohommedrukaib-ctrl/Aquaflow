"""
AquaFlow — Wash Board URLs (Feature-Enforced)
Powered by Quantum Axis

wash      → board + jobs
wash_bays → bay management
job_notes → job note printing
"""

from django.urls import path
from . import views
from apps.system.features import feature_required

urlpatterns = [
    path('',                         feature_required('wash')(views.wash_board),          name='wash_board'),
    path('board/data/',              feature_required('wash')(views.wash_board_data),     name='wash_board_data'),
    path('jobs/',                    feature_required('wash')(views.wash_job_list),       name='wash_job_list'),
    path('jobs/new/',                feature_required('wash')(views.wash_job_create),     name='wash_job_create'),
    path('jobs/create/',             feature_required('wash')(views.wash_job_create_ajax), name='wash_job_create_ajax'),
    path('jobs/<int:pk>/',           feature_required('wash')(views.wash_job_detail),     name='wash_job_detail'),
    path('jobs/<int:pk>/status/',    feature_required('wash')(views.update_status),       name='wash_update_status'),
    path('jobs/<int:pk>/employee/',  feature_required('wash')(views.assign_employee),     name='wash_assign_employee'),
    path('jobs/<int:pk>/bay/',       feature_required('wash_bays')(views.assign_bay),     name='wash_assign_bay'),
    path('jobs/<int:pk>/add-item/',  feature_required('wash')(views.wash_job_add_item),   name='wash_job_add_item'),
    path('jobs/<int:pk>/job-note/',  feature_required('job_notes')(views.generate_job_note), name='wash_job_note'),
]