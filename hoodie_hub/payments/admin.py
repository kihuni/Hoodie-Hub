from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['phone_number', 'mpesa_receipt_number']
    readonly_fields = ['id', 'created_at', 'updated_at']