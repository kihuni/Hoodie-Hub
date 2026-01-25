from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('payment/', views.payment_form, name='payment_form'),
    path('payment/initiate/', views.initiate_payment, name='initiate_payment'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    path('payment/receipt/<uuid:payment_id>/', views.download_receipt, name='download_receipt'),
    path('payment/status/<uuid:payment_id>/', views.payment_status, name='payment_status'),
]