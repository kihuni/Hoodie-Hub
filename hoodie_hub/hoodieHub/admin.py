from django.contrib import admin
from .models import Hoodie, Cart, CartItem, Order, OrderItem

@admin.register(Hoodie)
class HoodieAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock_quantity', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'stock_quantity']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'price')
        }),
        ('Inventory', {
            'fields': ('available_sizes', 'stock_quantity')
        }),
        ('Media', {
            'fields': ('image', 'image_url'),
            'description': 'Upload an image or provide an image URL'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['hoodie_name', 'size', 'quantity', 'price', 'get_subtotal']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'phone_number', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['customer_name', 'phone_number', 'mpesa_receipt_number']
    readonly_fields = ['id', 'checkout_request_id', 'merchant_request_id', 'mpesa_receipt_number', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer_name', 'phone_number', 'delivery_location')
        }),
        ('Order Details', {
            'fields': ('total_amount', 'status')
        }),
        ('M-Pesa Information', {
            'fields': ('checkout_request_id', 'merchant_request_id', 'mpesa_receipt_number'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['session_key', 'get_item_count', 'get_total', 'created_at']
    readonly_fields = ['session_key', 'created_at', 'updated_at']

admin.site.register(CartItem)