from django.urls import path
from . import views

urlpatterns = [
    path('',                             views.pos_home,               name='pos_home'),
    path('complete-sale/',               views.complete_sale,          name='pos_complete_sale'),
    path('receipt/<int:invoice_id>/',    views.receipt_view,           name='pos_receipt'),
    path('products/search/',             views.product_search_ajax,    name='pos_product_search'),
    path('products/quick-create/',       views.product_quick_create,   name='pos_product_quick_create'),
    path('service-price/',               views.service_price_for_vehicle, name='pos_service_price'),
    path('bookings/search/',             views.booking_search_ajax,    name='pos_booking_search'),
    path('wash-jobs/search/',            views.wash_job_search_ajax,   name='pos_wash_job_search'),
    path('wash-jobs/<int:pk>/items/',    views.wash_job_items_ajax,    name='pos_wash_job_items'),
]