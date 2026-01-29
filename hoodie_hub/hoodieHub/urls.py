from django.urls import path
from . import views

app_name = 'hoodieHub'

urlpatterns = [
    # SEO
    path('sitemap.xml', views.sitemap, name='sitemap'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.user_profile, name='user_profile'),
    
    # Product pages
    path('', views.home, name='home'),
    path('hoodie/<uuid:hoodie_id>/', views.hoodie_detail, name='hoodie_detail'),
    
    # Cart
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<uuid:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # Checkout
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/process/', views.process_checkout, name='process_checkout'),
    
    # M-Pesa
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
    
    # Orders
    path('order/<uuid:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('order/<uuid:order_id>/detail/', views.order_detail, name='order_detail'),
    path('order/<uuid:order_id>/status/', views.check_order_status, name='check_order_status'),
    path('order/<uuid:order_id>/receipt/', views.download_receipt, name='download_receipt'),
    
    # Cart Data
    path('cart/data/', views.get_cart_data, name='get_cart_data'),
]