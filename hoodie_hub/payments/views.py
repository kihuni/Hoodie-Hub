from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import Payment
from .mpesa import MpesaService
from .pdf_generator import OrderReceiptGenerator

def payment_form(request):
    """Display payment form"""
    return render(request, 'payments/payment_form.html')

def initiate_payment(request):
    """Initiate STK push"""
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        amount = request.POST.get('amount')
        description = request.POST.get('description', 'Payment')
        
        # Create payment record
        payment = Payment.objects.create(
            phone_number=phone_number,
            amount=amount,
            description=description
        )
        
        # Initiate STK push
        mpesa = MpesaService()
        response = mpesa.stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=str(payment.id),
            transaction_desc=description
        )
        
        # Update payment with M-Pesa details
        if response.get('ResponseCode') == '0':
            payment.merchant_request_id = response.get('MerchantRequestID')
            payment.checkout_request_id = response.get('CheckoutRequestID')
            payment.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Please check your phone to complete payment',
                'payment_id': str(payment.id)
            })
        else:
            payment.status = 'failed'
            payment.save()
            return JsonResponse({
                'success': False,
                'message': response.get('errorMessage', 'Payment failed')
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@csrf_exempt
@require_http_methods(["POST"])
def mpesa_callback(request):
    """Handle M-Pesa callback"""
    try:
        data = json.loads(request.body)
        
        # Extract callback data
        result_code = data['Body']['stkCallback']['ResultCode']
        checkout_request_id = data['Body']['stkCallback']['CheckoutRequestID']
        
        # Find payment
        payment = Payment.objects.get(checkout_request_id=checkout_request_id)
        
        if result_code == 0:
            # Payment successful
            callback_metadata = data['Body']['stkCallback']['CallbackMetadata']['Item']
            for item in callback_metadata:
                if item['Name'] == 'MpesaReceiptNumber':
                    payment.mpesa_receipt_number = item['Value']
            
            payment.status = 'completed'
        else:
            payment.status = 'failed'
        
        payment.save()
        
        return JsonResponse({'ResultCode': 0, 'ResultDesc': 'Accepted'})
    except Exception as e:
        return JsonResponse({'ResultCode': 1, 'ResultDesc': str(e)})

def download_receipt(request, payment_id):
    """Generate and download PDF receipt"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    if payment.status != 'completed':
        return HttpResponse('Payment not completed yet', status=400)
    
    # Generate PDF
    generator = OrderReceiptGenerator(payment)
    pdf_buffer = generator.generate()
    
    # Return PDF
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{payment.id}.pdf"'
    
    return response

def payment_status(request, payment_id):
    """Check payment status"""
    payment = get_object_or_404(Payment, id=payment_id)
    return JsonResponse({
        'status': payment.status,
        'amount': str(payment.amount),
        'phone_number': payment.phone_number,
        'receipt_number': payment.mpesa_receipt_number or ''
    })