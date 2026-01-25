import requests
import base64
from datetime import datetime
from decouple import config
import json

class MpesaService:
    def __init__(self):
        self.consumer_key = config('MPESA_CONSUMER_KEY')
        self.consumer_secret = config('MPESA_CONSUMER_SECRET')
        self.shortcode = config('MPESA_SHORTCODE')
        self.passkey = config('MPESA_PASSKEY')
        self.callback_url = config('MPESA_CALLBACK_URL')
        
        self.environment = config('MPESA_ENVIRONMENT', default='sandbox')
        
        if self.environment == 'sandbox':
            self.auth_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
            self.stk_push_url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
        else:
            self.auth_url = 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
            self.stk_push_url = 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
        
    def get_access_token(self):
        """Get OAuth access token"""
        try:
            response = requests.get(
                self.auth_url,
                auth=(self.consumer_key, self.consumer_secret)
            )
            response.raise_for_status()
            return response.json().get('access_token')
        except requests.exceptions.RequestException as e:
            print(f"Error getting access token: {e}")
            return None
    
    def generate_password(self):
        """Generate password for STK push"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        data_to_encode = f"{self.shortcode}{self.passkey}{timestamp}"
        encoded = base64.b64encode(data_to_encode.encode())
        return encoded.decode('utf-8'), timestamp
    
    def stk_push(self, phone_number, amount, account_reference, transaction_desc):
        """Initiate STK push"""
        access_token = self.get_access_token()
        
        if not access_token:
            return {
                'ResponseCode': '1',
                'errorMessage': 'Failed to get access token'
            }
        
        password, timestamp = self.generate_password()
        
        # Format phone number (remove leading 0, add 254)
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        elif phone_number.startswith('+254'):
            phone_number = phone_number[1:]
        elif not phone_number.startswith('254'):
            phone_number = '254' + phone_number
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'BusinessShortCode': self.shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': 'CustomerPayBillOnline',
            'Amount': int(amount),
            'PartyA': phone_number,
            'PartyB': self.shortcode,
            'PhoneNumber': phone_number,
            'CallBackURL': self.callback_url,
            'AccountReference': account_reference,
            'TransactionDesc': transaction_desc
        }
        
        try:
            response = requests.post(
                self.stk_push_url, 
                json=payload, 
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error initiating STK push: {e}")
            return {
                'ResponseCode': '1',
                'errorMessage': str(e)
            }