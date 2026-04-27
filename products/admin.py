from django.contrib import admin
from django.contrib import messages

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'sku',
        'price',
        'stock',
        'inventory_locked',
        'low_stock_threshold',
        'inventory_status_badge',
        'is_active',
        'updated_at',
    )
    list_filter = ('category', 'inventory_locked', 'is_active')
    search_fields = ('name', 'sku', 'description', 'category')
    readonly_fields = ('sku', 'created_at', 'updated_at')
    list_editable = ('price', 'stock', 'inventory_locked', 'low_stock_threshold', 'is_active')
    ordering = ('name',)
    actions = ('lock_inventory', 'unlock_inventory')
    fieldsets = (
        ('Product Details', {
            'fields': ('name', 'category', 'sku', 'description', 'image')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'stock', 'inventory_locked', 'low_stock_threshold', 'is_active')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    @admin.display(description='Inventory Status')
    def inventory_status_badge(self, obj):
        return obj.inventory_status

    @admin.action(description='Lock inventory for selected products')
    def lock_inventory(self, request, queryset):
        updated = queryset.update(inventory_locked=True)
        self.message_user(request, f'{updated} product(s) locked.', level=messages.SUCCESS)

    @admin.action(description='Unlock inventory for selected products')
    def unlock_inventory(self, request, queryset):
        updated = queryset.update(inventory_locked=False)
        self.message_user(request, f'{updated} product(s) unlocked.', level=messages.SUCCESS)
