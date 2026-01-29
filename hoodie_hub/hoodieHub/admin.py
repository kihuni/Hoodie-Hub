from django.contrib import admin
from django.utils.html import format_html
from .models import Hoodie, Cart, CartItem, Order, OrderItem, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['get_user_display', 'phone_number', 'delivery_location', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone_number']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at', 'user']
    
    def get_user_display(self, obj):
        return f"{obj.user.get_full_name() or obj.user.username}"
    get_user_display.short_description = "User"
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Contact Details', {
            'fields': ('phone_number',)
        }),
        ('Delivery Information', {
            'fields': ('delivery_location',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Hoodie)
class HoodieAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_price_display', 'get_stock_display', 'get_status_display', 'created_at']
    list_filter = ['is_active', 'created_at', 'available_sizes']
    search_fields = ['name', 'description']
    
    def get_price_display(self, obj):
        return format_html('<strong>KES {}</strong>', f'{obj.price:,.2f}')
    get_price_display.short_description = "Price"
    
    def get_stock_display(self, obj):
        if obj.stock_quantity > 10:
            color = 'green'
        elif obj.stock_quantity > 0:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} units</span>',
            color,
            obj.stock_quantity
        )
    get_stock_display.short_description = "Stock"
    
    def get_status_display(self, obj):
        color = 'green' if obj.is_active else 'red'
        status = 'Active' if obj.is_active else 'Inactive'
        return format_html(
            '<span style="color: {}; font-weight: bold;">●</span> {}',
            color,
            status
        )
    get_status_display.short_description = "Status"
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'price')
        }),
        ('Inventory', {
            'fields': ('available_sizes', 'stock_quantity'),
            'description': 'Manage product availability'
        }),
        ('Media', {
            'fields': ('image', 'image_url'),
            'description': 'Upload an image or provide an image URL'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['hoodie_name', 'size', 'quantity', 'price', 'get_subtotal_display']
    can_delete = False
    
    def get_subtotal_display(self, obj):
        subtotal = obj.get_subtotal()
        return format_html('<strong>KES {}</strong>', f'{subtotal:,.2f}')
    get_subtotal_display.short_description = "Subtotal"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['get_order_id', 'customer_name', 'user_display', 'get_status_badge', 'total_amount_display', 'created_at']
    list_filter = ['status', 'created_at', 'user']
    search_fields = ['customer_name', 'phone_number', 'mpesa_receipt_number', 'user__username', 'user__email']
    readonly_fields = ['id', 'checkout_request_id', 'merchant_request_id', 'mpesa_receipt_number', 'created_at', 'updated_at', 'get_total_amount_display', 'get_order_items']
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    
    def get_order_id(self, obj):
        return format_html('<code>{}</code>', str(obj.id)[:12])
    get_order_id.short_description = "Order ID"
    
    def user_display(self, obj):
        if obj.user:
            return format_html(
                '<a href="/admin/auth/user/{}/change/">{}</a>',
                obj.user.id,
                obj.user.get_full_name() or obj.user.username
            )
        return format_html('<em style="color: gray;">{}</em>', 'Guest')
    user_display.short_description = "User"
    
    def get_status_badge(self, obj):
        colors = {
            'PENDING': '#fbbf24',
            'PAID': '#60a5fa',
            'FULFILLED': '#34d399',
            'CANCELLED': '#f87171',
            'FAILED': '#ef4444'
        }
        color = colors.get(obj.status, '#9ca3af')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_badge.short_description = "Status"
    
    def total_amount_display(self, obj):
        return format_html('<strong style="color: green;">KES {}</strong>', f'{obj.total_amount:,.2f}')
    total_amount_display.short_description = "Total Amount"
    
    def get_total_amount_display(self, obj):
        return format_html(
            '<h3 style="color: green;">KES {}</h3>',
            f'{obj.total_amount:,.2f}'
        )
    get_total_amount_display.short_description = "Total Amount"
    
    def get_order_items(self, obj):
        items_html = '<table style="width: 100%; border-collapse: collapse;">'
        items_html += '<tr style="background-color: #f3f4f6;"><th style="border: 1px solid #e5e7eb; padding: 8px; text-align: left;">Item</th><th style="border: 1px solid #e5e7eb; padding: 8px; text-align: right;">Price</th><th style="border: 1px solid #e5e7eb; padding: 8px; text-align: center;">Qty</th><th style="border: 1px solid #e5e7eb; padding: 8px; text-align: right;">Subtotal</th></tr>'
        for item in obj.items.all():
            items_html += f'<tr><td style="border: 1px solid #e5e7eb; padding: 8px;">{item.hoodie_name} ({item.size})</td><td style="border: 1px solid #e5e7eb; padding: 8px; text-align: right;">KES {item.price:,.2f}</td><td style="border: 1px solid #e5e7eb; padding: 8px; text-align: center;">{item.quantity}</td><td style="border: 1px solid #e5e7eb; padding: 8px; text-align: right;">KES {item.get_subtotal():,.2f}</td></tr>'
        items_html += '</table>'
        return format_html('{}', items_html)
    get_order_items.short_description = "Order Items"
    
    fieldsets = (
        ('🛍️ Customer Information', {
            'fields': ('customer_name', 'user_display', 'phone_number', 'delivery_location')
        }),
        ('💰 Order Details', {
            'fields': ('get_total_amount_display', 'status', 'get_order_items')
        }),
        ('💳 M-Pesa Payment', {
            'fields': ('checkout_request_id', 'merchant_request_id', 'mpesa_receipt_number'),
            'classes': ('collapse',),
            'description': 'M-Pesa transaction details'
        }),
        ('📅 Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['get_cart_display', 'user_display', 'get_item_count_display', 'get_total_display', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['id', 'session_key', 'created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'session_key']
    
    def get_cart_display(self, obj):
        if obj.user:
            return format_html('👤 <strong>{}</strong>', obj.user.username)
        return format_html('🔗 <code>{}</code>', obj.session_key[:12])
    get_cart_display.short_description = "Cart"
    
    def user_display(self, obj):
        if obj.user:
            return format_html(
                '<a href="/admin/auth/user/{}/change/">{}</a>',
                obj.user.id,
                obj.user.get_full_name() or obj.user.username
            )
        return format_html('<em style="color: gray;">{}</em>', 'Guest Session')
    user_display.short_description = "User"
    
    def get_item_count_display(self, obj):
        count = obj.get_item_count()
        return format_html(
            '<span style="background-color: #dbeafe; color: #0369a1; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{} items</span>',
            count
        )
    get_item_count_display.short_description = "Items"
    
    def get_total_display(self, obj):
        return format_html('<strong style="color: green;">KES {}</strong>', f'{obj.get_total():,.2f}')
    get_total_display.short_description = "Total"
    
    fieldsets = (
        ('Cart Information', {
            'fields': ('id', 'user_display', 'session_key')
        }),
        ('Cart Details', {
            'fields': ('get_item_count_display', 'get_total_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['get_item_display', 'get_cart_display', 'quantity', 'get_subtotal_display']
    list_filter = ['created_at']
    search_fields = ['hoodie__name', 'cart__user__username']
    readonly_fields = ['id', 'created_at']
    
    def get_item_display(self, obj):
        return f"{obj.hoodie.name} ({obj.size})"
    get_item_display.short_description = "Item"
    
    def get_cart_display(self, obj):
        if obj.cart.user:
            return obj.cart.user.username
        return f"Guest ({obj.cart.session_key[:8]})"
    get_cart_display.short_description = "Cart"
    
    def get_subtotal_display(self, obj):
        return format_html('<strong>KES {}</strong>', f'{obj.get_subtotal():,.2f}')
    get_subtotal_display.short_description = "Subtotal"
