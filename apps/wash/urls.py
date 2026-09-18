from django.urls import path
from . import views

urlpatterns = [
    path('',                         views.wash_board,         name='wash_board'),
    path('board/data/',              views.wash_board_data,    name='wash_board_data'),
    path('jobs/',                    views.wash_job_list,      name='wash_job_list'),
    path('jobs/new/',                views.wash_job_create,    name='wash_job_create'),
    path('jobs/create/',             views.wash_job_create_ajax, name='wash_job_create_ajax'),
    path('jobs/<int:pk>/',           views.wash_job_detail,    name='wash_job_detail'),
    path('jobs/<int:pk>/status/',    views.update_status,      name='wash_update_status'),
    path('jobs/<int:pk>/employee/',  views.assign_employee,    name='wash_assign_employee'),
    path('jobs/<int:pk>/bay/',       views.assign_bay,         name='wash_assign_bay'),
    path('jobs/<int:pk>/add-item/',  views.wash_job_add_item,  name='wash_job_add_item'),
    path('jobs/<int:pk>/job-note/',  views.generate_job_note,  name='wash_job_note'),
]