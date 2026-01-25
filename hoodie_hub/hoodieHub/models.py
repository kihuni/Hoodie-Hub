from datetime import datetime
from django.db import models
import uuid

class Hoodie(models.Model):
    SIZE_CHOICES = [
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True)
    image = models.ImageField(upload_to='hoodies/', blank=True, null=True)
    available_sizes = models.CharField(max_length=50, default='S,M,L,XL') 
    stock_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    def get_sizes_list(self):
        return [size.strip() for size in self.available_sizes.split(',')]
    
    class Meta:
        ordering = ['-created_at']


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart {self.session_key}"
    
    def get_total(self):
        return sum(item.get_subtotal() for item in self.items.all())
    
    def get_item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    hoodie = models.ForeignKey(Hoodie, on_delete=models.CASCADE)
    size = models.CharField(max_length=5)
    quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.quantity}x {self.hoodie.name} ({self.size})"
    
    def get_subtotal(self):
        return self.hoodie.price * self.quantity
    
    class Meta:
        unique_together = ['cart', 'hoodie', 'size']


class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('FULFILLED', 'Fulfilled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15)
    delivery_location = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # M-Pesa fields
    checkout_request_id = models.CharField(max_length=100, blank=True)
    merchant_request_id = models.CharField(max_length=100, blank=True)
    mpesa_receipt_number = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Order {self.id} - {self.customer_name}"
    
    class Meta:
        ordering = ['-created_at']


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    hoodie_name = models.CharField(max_length=200) 
    size = models.CharField(max_length=5)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  
    
    def __str__(self):
        return f"{self.quantity}x {self.hoodie_name} ({self.size})"
    
    def get_subtotal(self):
        return self.price * self.quantity
