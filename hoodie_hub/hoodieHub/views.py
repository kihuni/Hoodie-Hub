from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.db import IntegrityError
import json
from .models import Hoodie, Cart, CartItem, Order, OrderItem, UserProfile
from  payments.mpesa import MpesaService
from payments.pdf_generator import OrderReceiptGenerator
import uuid

# ========== AUTHENTICATION VIEWS ==========

def register(request):
    """User registration page"""
    if request.user.is_authenticated:
        return redirect('hoodieHub:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone_number = request.POST.get('phone_number', '')
        
        # Validate passwords match
        if password != password_confirm:
            return render(request, 'hoodieHub/register.html', {
                'error': 'Passwords do not match'
            })
        
        # Check username availability
        if User.objects.filter(username=username).exists():
            return render(request, 'hoodieHub/register.html', {
                'error': 'Username already taken'
            })
        
        # Check email availability
        if User.objects.filter(email=email).exists():
            return render(request, 'hoodieHub/register.html', {
                'error': 'Email already registered'
            })
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Get or create user profile (handle signal timing)
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            user_profile.phone_number = phone_number
            user_profile.save()
            
            # Show success message and prompt user to login
            return render(request, 'hoodieHub/register.html', {
                'success': 'Registration successful! Please log in with your credentials.',
                'show_login_prompt': True
            })
        
        except IntegrityError:
            return render(request, 'hoodieHub/register.html', {
                'error': 'This username or email is already registered. Please try another or login.'
            })
        except Exception as e:
            return render(request, 'hoodieHub/register.html', {
                'error': 'Something went wrong during registration. Please try again.'
            })
    
    return render(request, 'hoodieHub/register.html')


def login_view(request):
    """User login page"""
    if request.user.is_authenticated:
        return redirect('hoodieHub:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Merge session cart with user cart if exists
            if 'cart_session' in request.session:
                old_session_key = request.session['cart_session']
                try:
                    old_cart = Cart.objects.get(session_key=old_session_key)
                    # Get or create user cart
                    user_cart, created = Cart.objects.get_or_create(user=user)
                    # Move items to user cart
                    for item in old_cart.items.all():
                        existing_item = CartItem.objects.filter(
                            cart=user_cart,
                            hoodie=item.hoodie,
                            size=item.size
                        ).first()
                        if existing_item:
                            existing_item.quantity += item.quantity
                            existing_item.save()
                        else:
                            item.cart = user_cart
                            item.save()
                    # Delete old session cart
                    old_cart.delete()
                except Cart.DoesNotExist:
                    pass
                del request.session['cart_session']
            
            # Redirect to home after successful login
            return redirect('hoodieHub:home')
        else:
            return render(request, 'hoodieHub/login.html', {
                'error': 'Invalid username or password'
            })
    
    return render(request, 'hoodieHub/login.html')


def logout_view(request):
    """User logout"""
    # Convert user cart to session cart if user is logged in
    if request.user.is_authenticated:
        try:
            user_cart = Cart.objects.get(user=request.user)
            # Create new session cart
            request.session['cart_session'] = str(uuid.uuid4())
            session_cart = Cart.objects.create(session_key=request.session['cart_session'])
            # Move items to session cart
            for item in user_cart.items.all():
                item.cart = session_cart
                item.save()
            # Delete user cart
            user_cart.delete()
        except Cart.DoesNotExist:
            request.session['cart_session'] = str(uuid.uuid4())
    
    logout(request)
    return redirect('hoodieHub:home')


@login_required(login_url='hoodieHub:login')
def order_detail(request, order_id):
    """View and manage order details"""
    order = get_object_or_404(Order, id=order_id)
    
    # Check if user owns this order
    if order.user != request.user and not request.user.is_staff:
        return redirect('hoodieHub:login')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Only allow cancellation of PENDING orders
        if action == 'cancel' and order.status == 'PENDING':
            order.status = 'CANCELLED'
            order.save()
            return render(request, 'hoodieHub/order_detail.html', {
                'order': order,
                'success': 'Order has been cancelled successfully'
            })
        elif action == 'cancel' and order.status != 'PENDING':
            return render(request, 'hoodieHub/order_detail.html', {
                'order': order,
                'error': 'Only pending orders can be cancelled'
            })
    
    return render(request, 'hoodieHub/order_detail.html', {
        'order': order
    })


@login_required(login_url='hoodieHub:login')
def user_profile(request):
    """User profile page with order history"""
    profile = request.user.profile
    # Get active orders (not cancelled)
    active_orders = Order.objects.filter(user=request.user).exclude(status='CANCELLED').prefetch_related('items').order_by('-created_at')
    # Get cancelled orders
    cancelled_orders = Order.objects.filter(user=request.user, status='CANCELLED').prefetch_related('items').order_by('-created_at')
    
    if request.method == 'POST':
        request.user.first_name = request.POST.get('first_name', '')
        request.user.last_name = request.POST.get('last_name', '')
        request.user.email = request.POST.get('email', '')
        request.user.save()
        
        profile.phone_number = request.POST.get('phone_number', '')
        profile.delivery_location = request.POST.get('delivery_location', '')
        profile.save()
        
        return render(request, 'hoodieHub/profile.html', {
            'profile': profile,
            'active_orders': active_orders,
            'cancelled_orders': cancelled_orders,
            'success': 'Profile updated successfully'
        })
    
    return render(request, 'hoodieHub/profile.html', {
        'profile': profile,
        'active_orders': active_orders,
        'cancelled_orders': cancelled_orders
    })


# ========== PRODUCT VIEWS ==========

def home(request):
    """Homepage - List all hoodies"""
    hoodies = Hoodie.objects.filter(is_active=True)
    
    # Get cart count for display
    cart_count = 0
    if 'cart_session' in request.session:
        try:
            cart = Cart.objects.get(session_key=request.session['cart_session'])
            cart_count = cart.get_item_count()
        except Cart.DoesNotExist:
            pass
    
    return render(request, 'hoodieHub/home.html', {
        'hoodies': hoodies,
        'cart_count': cart_count
    })

def hoodie_detail(request, hoodie_id):
    """Single hoodie detail page"""
    hoodie = get_object_or_404(Hoodie, id=hoodie_id)
    sizes = hoodie.get_sizes_list()
    
    return render(request, 'hoodieHub/hoodie_detail.html', {
        'hoodie': hoodie,
        'sizes': sizes
    })

# ========== CART VIEWS ==========

def get_or_create_cart(request):
    """Get or create cart for current session or user"""
    if request.user.is_authenticated:
        # For authenticated users, use user-based cart
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        # For anonymous users, use session-based cart
        if 'cart_session' not in request.session:
            request.session['cart_session'] = str(uuid.uuid4())
        
        cart, created = Cart.objects.get_or_create(
            session_key=request.session['cart_session']
        )
    
    return cart

def add_to_cart(request):
    """Add hoodie to cart with stock validation"""
    if request.method == 'POST':
        hoodie_id = request.POST.get('hoodie_id')
        size = request.POST.get('size')
        quantity = int(request.POST.get('quantity', 1))
        
        hoodie = get_object_or_404(Hoodie, id=hoodie_id)
        
        # Check stock
        if hoodie.stock_quantity <= 0:
            return JsonResponse({
                'success': False,
                'message': f'{hoodie.name} is out of stock'
            })
        
        # Check if quantity requested exceeds stock
        if quantity > hoodie.stock_quantity:
            return JsonResponse({
                'success': False,
                'message': f'Only {hoodie.stock_quantity} items available in stock'
            })
        
        cart = get_or_create_cart(request)
        
        # Check if item already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            hoodie=hoodie,
            size=size,
            defaults={'quantity': quantity}
        )
        
        if not created:
            # Check if total quantity would exceed stock
            if (cart_item.quantity + quantity) > hoodie.stock_quantity:
                return JsonResponse({
                    'success': False,
                    'message': f'Only {hoodie.stock_quantity} items available. You already have {cart_item.quantity} in cart'
                })
            cart_item.quantity += quantity
            cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{hoodie.name} added to cart',
            'cart_count': cart.get_item_count()
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def view_cart(request):
    """View cart page"""
    cart = get_or_create_cart(request)
    
    return render(request, 'hoodieHub/cart.html', {
        'cart': cart
    })

def update_cart_item(request):
    """Update cart item quantity"""
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 1))
        
        cart_item = get_object_or_404(CartItem, id=item_id)
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
        
        return JsonResponse({
            'success': True,
            'cart_total': cart_item.cart.get_total()
        })
    
    return JsonResponse({'success': False})

def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart = cart_item.cart
    cart_item.delete()
    
    return redirect('hoodieHub:view_cart')

# ========== CHECKOUT VIEWS ==========

def checkout(request):
    """Checkout page"""
    cart = get_or_create_cart(request)
    
    if cart.get_item_count() == 0:
        return redirect('hoodieHub:home')
    
    return render(request, 'hoodieHub/checkout.html', {
        'cart': cart
    })

def process_checkout(request):
    """Process checkout and initiate M-Pesa payment"""
    if request.method == 'POST':
        # Get customer details
        customer_name = request.POST.get('customer_name')
        phone_number = request.POST.get('phone_number')
        delivery_location = request.POST.get('delivery_location')
        
        # Get cart
        cart = get_or_create_cart(request)
        
        if cart.get_item_count() == 0:
            return JsonResponse({
                'success': False,
                'message': 'Your cart is empty'
            })
        
        # Create order
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            customer_name=customer_name,
            phone_number=phone_number,
            delivery_location=delivery_location,
            total_amount=cart.get_total(),
            status='PENDING'
        )
        
        # Create order items from cart
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                hoodie_name=cart_item.hoodie.name,
                size=cart_item.size,
                quantity=cart_item.quantity,
                price=cart_item.hoodie.price
            )
        
        # Initiate M-Pesa STK Push
        mpesa = MpesaService()
        response = mpesa.stk_push(
            phone_number=phone_number,
            amount=order.total_amount,
            account_reference=f"ORDER-{order.id}",
            transaction_desc=f"HoodieHub Order"
        )
        
        if response.get('ResponseCode') == '0':
            # Update order with M-Pesa details
            order.checkout_request_id = response.get('CheckoutRequestID')
            order.merchant_request_id = response.get('MerchantRequestID')
            order.save()
            
            # Clear cart
            cart.items.all().delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Please check your phone to complete payment',
                'order_id': str(order.id)
            })
        else:
            order.status = 'FAILED'
            order.save()
            
            return JsonResponse({
                'success': False,
                'message': response.get('errorMessage', 'Payment failed')
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

# ========== M-PESA CALLBACK ==========

@csrf_exempt
@require_http_methods(["POST"])
def mpesa_callback(request):
    """Handle M-Pesa payment callback"""
    try:
        data = json.loads(request.body)
        
        result_code = data['Body']['stkCallback']['ResultCode']
        checkout_request_id = data['Body']['stkCallback']['CheckoutRequestID']
        
        # Find order
        order = Order.objects.get(checkout_request_id=checkout_request_id)
        
        if result_code == 0:
            # Payment successful
            callback_metadata = data['Body']['stkCallback']['CallbackMetadata']['Item']
            for item in callback_metadata:
                if item['Name'] == 'MpesaReceiptNumber':
                    order.mpesa_receipt_number = item['Value']
            
            order.status = 'PAID'
        else:
            order.status = 'FAILED'
        
        order.save()
        
        return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})
    except Exception as e:
        return JsonResponse({'ResultCode': 1, 'ResultDesc': str(e)})

# ========== ORDER VIEWS ==========

def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id)
    
    return render(request, 'hoodieHub/order_confirmation.html', {
        'order': order
    })

def check_order_status(request, order_id):
    """Check order payment status (AJAX)"""
    order = get_object_or_404(Order, id=order_id)
    
    return JsonResponse({
        'status': order.status,
        'mpesa_receipt': order.mpesa_receipt_number or ''
    })

def download_receipt(request, order_id):
    """Download order receipt PDF"""
    order = get_object_or_404(Order, id=order_id)
    
    if order.status != 'PAID':
        return HttpResponse('Order not paid yet', status=400)
    
    # Generate PDF
    generator = OrderReceiptGenerator(order)
    pdf_buffer = generator.generate()
    
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{order.id}.pdf"'
    
    return response


# ========== SEO ==========

def sitemap(request):
    """Generate XML sitemap for search engines"""
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    xml += 'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
    
    # Get the domain
    domain = request.build_absolute_uri('/').rstrip('/')
    
    # Static pages with high priority
    static_urls = [
        (reverse('hoodieHub:home'), '1.0', 'weekly'),
        (reverse('hoodieHub:view_cart'), '0.8', 'weekly'),
    ]
    
    for url, priority, changefreq in static_urls:
        full_url = f"{domain}{url}"
        xml += f'  <url>\n'
        xml += f'    <loc>{full_url}</loc>\n'
        xml += f'    <priority>{priority}</priority>\n'
        xml += f'    <changefreq>{changefreq}</changefreq>\n'
        xml += f'  </url>\n'
    
    # Product pages
    hoodies = Hoodie.objects.all()
    for hoodie in hoodies:
        url = reverse('hoodieHub:hoodie_detail', args=[hoodie.id])
        full_url = f"{domain}{url}"
        
        xml += f'  <url>\n'
        xml += f'    <loc>{full_url}</loc>\n'
        xml += f'    <lastmod>{hoodie.created_at.isoformat() if hasattr(hoodie, "created_at") else ""}</lastmod>\n'
        xml += f'    <priority>0.9</priority>\n'
        xml += f'    <changefreq>monthly</changefreq>\n'
        
        # Add image if available
        if hoodie.image:
            image_url = f"{domain}{hoodie.image.url}"
            xml += f'    <image:image>\n'
            xml += f'      <image:loc>{image_url}</image:loc>\n'
            xml += f'      <image:title>{hoodie.name}</image:title>\n'
            xml += f'    </image:image>\n'
        
        xml += f'  </url>\n'
    
    xml += '</urlset>'
    
    return HttpResponse(xml, content_type='application/xml')


# ========== CART DATA ==========

def get_cart_data(request):
    """Get cart data as JSON for AJAX updates"""
    cart = get_or_create_cart(request)
    
    items = []
    for item in cart.items.all():
        items.append({
            'id': str(item.id),
            'hoodie_name': item.hoodie.name,
            'size': item.size,
            'quantity': item.quantity,
            'price': str(item.hoodie.price),
            'subtotal': str(item.get_subtotal())
        })
    
    return JsonResponse({
        'item_count': cart.get_item_count(),
        'total': str(cart.get_total()),
        'items': items
    })