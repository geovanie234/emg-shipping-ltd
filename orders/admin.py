from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import (
    DeliveryZone,
    Order,
    OrderItem,
    OrderReview,
    Payment,
    SMSNotification,
    TrackingUpdate,
)
from .services import transition_order_status


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price',)


class TrackingUpdateInline(admin.TabularInline):
    model = TrackingUpdate
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'user',
        'full_name',
        'district',
        'status',
        'payment_status',
        'inventory_locked',
        'order_total',
        'created_at',
    )
    list_filter = ('status', 'payment_status', 'district', 'payment_method', 'inventory_locked', 'created_at')
    search_fields = ('order_number', 'tracking_number', 'full_name', 'phone', 'email')
    readonly_fields = ('order_number', 'tracking_number', 'created_at', 'updated_at', 'inventory_locked')
    inlines = [OrderItemInline, TrackingUpdateInline]
    actions = ('mark_processing', 'mark_shipped', 'mark_delivered', 'mark_cancelled')
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'tracking_number', 'user', 'status', 'payment_status', 'inventory_locked')
        }),
        ('Customer Details', {
            'fields': ('full_name', 'phone', 'email', 'address', 'district', 'city')
        }),
        ('Payment & Delivery', {
            'fields': ('payment_method', 'delivery_fee', 'estimated_delivery', 'actual_delivery')
        }),
        ('Tracking', {
            'fields': ('current_latitude', 'current_longitude', 'current_location')
        }),
        ('Additional Info', {
            'fields': ('sms_opt_in', 'sms_notification_sent', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    @admin.display(description='Order Total')
    def order_total(self, obj):
        return f"{obj.total_price()} RWF"

    @admin.action(description='Mark selected orders as Processing')
    def mark_processing(self, request, queryset):
        self._bulk_update_status(request, queryset, 'Processing')

    @admin.action(description='Mark selected orders as Shipped')
    def mark_shipped(self, request, queryset):
        self._bulk_update_status(request, queryset, 'Shipped')

    @admin.action(description='Mark selected orders as Delivered')
    def mark_delivered(self, request, queryset):
        self._bulk_update_status(request, queryset, 'Delivered')

    @admin.action(description='Mark selected orders as Cancelled')
    def mark_cancelled(self, request, queryset):
        self._bulk_update_status(request, queryset, 'Cancelled')

    def _bulk_update_status(self, request, queryset, status):
        updated = 0
        failures = 0
        for order in queryset.prefetch_related('items__product'):
            try:
                transition_order_status(
                    order,
                    status,
                    updated_by=request.user,
                    description=f'Order updated to {status} from Django admin.',
                )
                updated += 1
            except ValidationError:
                failures += 1
        self.message_user(request, f'{updated} order(s) updated to {status}.', level=messages.SUCCESS)
        if failures:
            self.message_user(request, f'{failures} order(s) could not be updated.', level=messages.WARNING)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'total_price_display')
    list_filter = ('order__status',)
    search_fields = ('order__order_number', 'product__name', 'product__sku')

    @admin.display(description='Total')
    def total_price_display(self, obj):
        return f"{obj.total_price()} RWF"


@admin.register(TrackingUpdate)
class TrackingUpdateAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'location', 'updated_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__order_number', 'location', 'description')


@admin.register(OrderReview)
class OrderReviewAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'rating', 'delivery_rating', 'created_at', 'is_approved')
    list_filter = ('rating', 'is_approved', 'created_at')
    search_fields = ('order__order_number', 'user__username')
    actions = ('approve_reviews',)

    @admin.action(description='Approve selected reviews')
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)


@admin.register(SMSNotification)
class SMSNotificationAdmin(admin.ModelAdmin):
    list_display = ('order', 'phone_number', 'type', 'status', 'created_at')
    list_filter = ('status', 'type', 'created_at')
    search_fields = ('order__order_number', 'phone_number')


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_fee', 'free_delivery_threshold', 'estimated_delivery_hours', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'districts')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'transaction_id', 'amount', 'method', 'status', 'created_at')
    list_filter = ('method', 'status', 'created_at')
    search_fields = ('order__order_number', 'transaction_id')
