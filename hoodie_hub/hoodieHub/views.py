from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import Hoodie, Cart, CartItem, Order, OrderItem
from  payments.mpesa import MpesaService
from payments.pdf_generator import OrderReceiptGenerator
import uuid

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
    """Get or create cart for current session"""
    if 'cart_session' not in request.session:
        request.session['cart_session'] = str(uuid.uuid4())
    
    cart, created = Cart.objects.get_or_create(
        session_key=request.session['cart_session']
    )
    return cart

def add_to_cart(request):
    """Add hoodie to cart"""
    if request.method == 'POST':
        hoodie_id = request.POST.get('hoodie_id')
        size = request.POST.get('size')
        quantity = int(request.POST.get('quantity', 1))
        
        hoodie = get_object_or_404(Hoodie, id=hoodie_id)
        cart = get_or_create_cart(request)
        
        # Check if item already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            hoodie=hoodie,
            size=size,
            defaults={'quantity': quantity}
        )
        
        if not created:
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
        return redirect('payments:home')
    
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