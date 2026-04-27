from django.db import models
from django.conf import settings
from products.models import Product
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from decimal import Decimal


class Order(models.Model):
    """
    Main Order model for EMG Shipping Rwanda
    Handles all order information, tracking, and status
    """

    DISTRICT_CHOICES = [
        ('Gasabo', 'Gasabo'),
        ('Kicukiro', 'Kicukiro'),
        ('Nyarugenge', 'Nyarugenge'),
    ]

    PAYMENT_CHOICES = [
        ('Cash on Delivery', 'Cash on Delivery'),
        ('MTN Mobile Money', 'MTN Mobile Money'),
        ('Airtel Money', 'Airtel Money'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded')
    ]

    # Order Identification - ALL NULLABLE FOR MIGRATION
    order_number = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False, 
        null=True,          # Added null=True
        blank=True,         # Added blank=True
        help_text="Unique order identifier (EMG-XXXXXXXX)"
    )
    tracking_number = models.CharField(
        max_length=50, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="Public tracking number for customers"
    )
    
    # User Relationship
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='orders',
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Customer who placed the order"
    )

    # Customer Details
    full_name = models.CharField(
        max_length=100,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Full name of customer"
    )
    phone = models.CharField(
        max_length=15,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Contact phone number"
    )
    address = models.CharField(
        max_length=255,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Delivery address"
    )
    email = models.EmailField(
        blank=True, 
        null=True,
        help_text="Optional email for notifications"
    )

    # Location
    district = models.CharField(
        max_length=100, 
        choices=DISTRICT_CHOICES,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Kigali district for delivery"
    )
    city = models.CharField(
        max_length=100, 
        default='Kigali',
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="City (defaults to Kigali)"
    )

    # Payment & Delivery
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_CHOICES,
        default='Cash on Delivery',
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Selected payment method"
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=2000,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Delivery fee in RWF"
    )
    
    # Payment Status
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='Pending',
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Current payment status"
    )

    # Order Status
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Pending',
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Current order status"
    )
    inventory_locked = models.BooleanField(
        default=False,
        help_text="Whether stock has already been reserved for this order"
    )

    # Tracking Information
    estimated_delivery = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Estimated delivery date and time"
    )
    actual_delivery = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Actual delivery date and time"
    )
    
    # Location Tracking (for map)
    current_latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        help_text="Current latitude for tracking"
    )
    current_longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        help_text="Current longitude for tracking"
    )
    current_location = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="Current location description"
    )

    # SMS Notifications
    sms_notification_sent = models.BooleanField(
        default=False,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Whether SMS notification has been sent"
    )
    sms_opt_in = models.BooleanField(
        default=True,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Customer opted in for SMS updates"
    )

    # Order Notes
    notes = models.TextField(
        blank=True, 
        null=True, 
        help_text="Special instructions for delivery"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Order creation date and time"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Last update date and time"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['tracking_number']),
            models.Index(fields=['status']),
            models.Index(fields=['user', '-created_at']),
        ]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def save(self, *args, **kwargs):
        """Generate order and tracking numbers if not exists"""
        # Generate order number if not exists
        if not self.order_number:
            self.order_number = f"EMG-{uuid.uuid4().hex[:8].upper()}"
        
        # Generate tracking number if not exists
        if not self.tracking_number:
            self.tracking_number = f"TRK-{uuid.uuid4().hex[:10].upper()}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number or 'No Order Number'} - {self.status or 'No Status'}"

    def total_price(self):
        """Calculate total order price including delivery fee"""
        total = sum((item.total_price() for item in self.items.all()), Decimal('0.00'))
        return total + (self.delivery_fee or Decimal('0.00'))

    def subtotal(self):
        """Calculate subtotal without delivery fee"""
        return sum((item.total_price() for item in self.items.all()), Decimal('0.00'))

    def get_status_percentage(self):
        """Get progress percentage for tracking progress bar"""
        status_progress = {
            'Pending': 25,
            'Processing': 50,
            'Shipped': 75,
            'Delivered': 100,
            'Cancelled': 0
        }
        return status_progress.get(self.status, 0)

    def get_tracking_history(self):
        """Return list of status updates ordered by date"""
        return self.tracking_updates.all()

    def can_cancel(self):
        """Check if order can be cancelled by customer"""
        return self.status in ['Pending', 'Processing']

    def can_review(self):
        """Check if order can be reviewed by customer"""
        return self.status == 'Delivered'

    def time_since_order(self):
        """Get human-readable time since order was placed"""
        from django.utils import timesince
        return timesince.timesince(self.created_at) if self.created_at else "Unknown"

    def get_delivery_status(self):
        """Get human-readable delivery status message"""
        if self.status == 'Delivered':
            if self.actual_delivery:
                return f"Delivered on {self.actual_delivery.strftime('%b %d, %Y at %H:%M')}"
            return "Delivered"
        elif self.status == 'Shipped':
            if self.estimated_delivery:
                return f"Shipped - Expected by {self.estimated_delivery.strftime('%b %d, %Y')}"
            return "Shipped"
        elif self.status == 'Processing':
            return "Processing your order"
        elif self.status == 'Pending':
            return "Order received, awaiting processing"
        elif self.status == 'Cancelled':
            return "Order cancelled"
        return "Processing"

    def get_status_color(self):
        """Get Bootstrap color class for status badge"""
        colors = {
            'Pending': 'warning',
            'Processing': 'info',
            'Shipped': 'primary',
            'Delivered': 'success',
            'Cancelled': 'danger'
        }
        return colors.get(self.status, 'secondary')

    def item_count(self):
        """Get total number of items in order"""
        return self.items.count()

    def formatted_phone(self):
        """Format phone number for display"""
        if not self.phone:
            return ""
        phone = self.phone
        if len(phone) == 10:
            return f"{phone[:3]} {phone[3:6]} {phone[6:]}"
        return phone


class OrderItem(models.Model):
    """
    Individual items within an order
    """
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='items',
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Parent order"
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Product ordered"
    )
    quantity = models.IntegerField(
        default=1, 
        validators=[MinValueValidator(1)],
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Quantity ordered"
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Price at time of purchase"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Item addition date"
    )

    class Meta:
        ordering = ['created_at']
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def save(self, *args, **kwargs):
        """Save product price at time of order if not set"""
        if not self.price and self.product:
            self.price = self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        product_name = self.product.name if self.product else "Unknown Product"
        return f"{product_name} x {self.quantity or 0}"

    def total_price(self):
        """Calculate total for this item"""
        return (self.price or 0) * (self.quantity or 0)

    def get_discount(self):
        """Calculate any discount applied (for future use)"""
        if self.product and self.price:
            original = self.product.price * (self.quantity or 0)
            return original - self.total_price()
        return 0

    def formatted_price(self):
        """Format price with RWF"""
        return f"{self.price or 0} RWF"

    def formatted_total(self):
        """Format total with RWF"""
        return f"{self.total_price()} RWF"


class TrackingUpdate(models.Model):
    """
    Track order location and status updates in real-time
    """
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='tracking_updates',
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Order being tracked"
    )
    status = models.CharField(
        max_length=50, 
        choices=Order.STATUS_CHOICES,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Status at this update"
    )
    location = models.CharField(
        max_length=200,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Location description"
    )
    description = models.TextField(
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Detailed update description"
    )
    
    # Location coordinates
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        help_text="GPS latitude"
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        help_text="GPS longitude"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Update timestamp"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Admin who created this update"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', '-created_at']),
        ]
        verbose_name = "Tracking Update"
        verbose_name_plural = "Tracking Updates"

    def __str__(self):
        order_num = self.order.order_number if self.order else "No Order"
        return f"{order_num} - {self.status or 'No Status'} at {self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else 'Unknown'}"

    def get_location_name(self):
        """Get formatted location name with coordinates"""
        if self.latitude and self.longitude:
            return f"{self.location or 'Unknown'} ({self.latitude}, {self.longitude})"
        return self.location or "Unknown"

    def time_since(self):
        """Get time since this update"""
        from django.utils import timesince
        return timesince.timesince(self.created_at) if self.created_at else "Unknown"

    def get_status_color(self):
        """Get Bootstrap color class for status badge"""
        colors = {
            'Pending': 'warning',
            'Processing': 'info',
            'Shipped': 'primary',
            'Delivered': 'success',
            'Cancelled': 'danger'
        }
        return colors.get(self.status, 'secondary')


class OrderReview(models.Model):
    """
    Customer reviews and ratings for delivered orders
    """
    order = models.OneToOneField(
        Order, 
        on_delete=models.CASCADE, 
        related_name='review',
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Order being reviewed"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Customer who wrote the review"
    )
    
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Product rating (1-5 stars)"
    )
    delivery_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Delivery service rating (1-5 stars)"
    )
    comment = models.TextField(
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Review comment"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Review submission date"
    )
    is_approved = models.BooleanField(
        default=False,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Whether review is approved for display"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Order Review"
        verbose_name_plural = "Order Reviews"

    def __str__(self):
        order_num = self.order.order_number if self.order else "No Order"
        return f"Review for {order_num} - {self.rating or 0} stars"

    def average_rating(self):
        """Calculate average of product and delivery ratings"""
        return ((self.rating or 0) + (self.delivery_rating or 0)) / 2

    def get_rating_stars(self):
        """Return HTML stars for rating display"""
        stars = '*' * (self.rating or 0) + '-' * (5 - (self.rating or 0))
        return stars

    def formatted_date(self):
        """Format creation date"""
        return self.created_at.strftime('%b %d, %Y') if self.created_at else "Unknown"


class SMSNotification(models.Model):
    """
    Track all SMS notifications sent to customers
    """
    NOTIFICATION_TYPES = [
        ('order_confirmation', 'Order Confirmation'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('status_update', 'Status Update')
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered')
    ]

    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='sms_notifications',
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Related order"
    )
    phone_number = models.CharField(
        max_length=15,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Recipient phone number"
    )
    message = models.TextField(
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="SMS content"
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Delivery status"
    )
    type = models.CharField(
        max_length=50, 
        choices=NOTIFICATION_TYPES,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Type of notification"
    )
    
    provider_response = models.TextField(
        blank=True, 
        null=True,
        help_text="Response from SMS provider"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="When SMS was created"
    )
    sent_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When SMS was actually sent"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "SMS Notification"
        verbose_name_plural = "SMS Notifications"

    def __str__(self):
        return f"SMS to {self.phone_number or 'Unknown'} - {self.status or 'Unknown'}"

    def is_delivered(self):
        """Check if SMS was delivered"""
        return self.status == 'delivered'

    def time_until_sent(self):
        """Calculate time between creation and sending"""
        if self.sent_at and self.created_at:
            return self.sent_at - self.created_at
        return None


class DeliveryZone(models.Model):
    """
    Define delivery zones and pricing for Kigali districts
    """
    name = models.CharField(
        max_length=100,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Zone name (e.g., Gasabo Zone)"
    )
    districts = models.CharField(
        max_length=255, 
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Comma-separated list of districts"
    )
    base_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=2000,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Base delivery fee in RWF"
    )
    free_delivery_threshold = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=50000,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Orders above this amount get free delivery"
    )
    estimated_delivery_hours = models.IntegerField(
        default=24,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Estimated delivery time in hours"
    )
    is_active = models.BooleanField(
        default=True,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Whether this zone is currently active"
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Delivery Zone"
        verbose_name_plural = "Delivery Zones"

    def __str__(self):
        return self.name or "Unnamed Zone"

    def get_districts_list(self):
        """Return list of districts in this zone"""
        if not self.districts:
            return []
        return [d.strip() for d in self.districts.split(',')]

    def formatted_fee(self):
        """Format fee with RWF"""
        return f"{self.base_fee or 0} RWF"

    def formatted_threshold(self):
        """Format threshold with RWF"""
        return f"{self.free_delivery_threshold or 0} RWF"


class Payment(models.Model):
    """
    Track all payment transactions
    """
    PAYMENT_METHODS = [
        ('cash', 'Cash on Delivery'),
        ('mtn_momo', 'MTN Mobile Money'),
        ('airtel_money', 'Airtel Money'),
        ('card', 'Credit/Debit Card'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    order = models.OneToOneField(
        Order, 
        on_delete=models.CASCADE, 
        related_name='payment',
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Order being paid for"
    )
    transaction_id = models.CharField(
        max_length=100, 
        unique=True,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Unique transaction identifier"
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Payment amount in RWF"
    )
    
    method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHODS,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Payment method used"
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="Current payment status"
    )
    provider_response = models.JSONField(
        null=True, 
        blank=True,
        help_text="Raw response from payment provider"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,           # Added null=True
        blank=True,          # Added blank=True
        help_text="When payment was initiated"
    )
    completed_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When payment was completed"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"{self.transaction_id or 'No Transaction'} - {self.amount or 0} RWF - {self.status or 'Unknown'}"

    def formatted_amount(self):
        """Format amount with RWF"""
        return f"{self.amount or 0} RWF"

    def is_completed(self):
        """Check if payment is completed"""
        return self.status == 'completed'

    def time_to_complete(self):
        """Calculate time to complete payment"""
        if self.completed_at and self.created_at:
            return self.completed_at - self.created_at
        return None

    def get_method_display_with_icon(self):
        """Get payment method with icon class"""
        icons = {
            'cash': 'bi-cash',
            'mtn_momo': 'bi-phone text-warning',
            'airtel_money': 'bi-phone text-danger',
            'card': 'bi-credit-card'
        }
        return {
            'method': self.get_method_display() if self.method else "Unknown",
            'icon': icons.get(self.method, 'bi-credit-card')
        }
