from collections import Counter
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Prefetch, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from products.models import Product

from .models import Order, OrderItem, TrackingUpdate


MONEY_FIELD = DecimalField(max_digits=12, decimal_places=2)
INTEGER_VALUE_ZERO = Value(0)
DECIMAL_VALUE_ZERO = Value(Decimal('0.00'), output_field=MONEY_FIELD)
ORDER_LINE_TOTAL = ExpressionWrapper(F('items__price') * F('items__quantity'), output_field=MONEY_FIELD)
PRODUCT_LINE_TOTAL = ExpressionWrapper(F('orderitem__price') * F('orderitem__quantity'), output_field=MONEY_FIELD)
NON_CANCELLED_STATUSES = ['Pending', 'Processing', 'Shipped', 'Delivered']


def get_status_location(status):
    locations = {
        'Pending': 'Order Processing Center',
        'Processing': 'Warehouse',
        'Shipped': 'In Transit',
        'Delivered': 'Customer Location',
        'Cancelled': 'System',
    }
    return locations.get(status, 'Unknown')


def annotate_orders_with_totals(queryset):
    return queryset.annotate(
        items_count=Coalesce(Sum('items__quantity'), INTEGER_VALUE_ZERO),
        subtotal_amount=Coalesce(Sum(ORDER_LINE_TOTAL), DECIMAL_VALUE_ZERO),
        delivery_fee_amount=Coalesce('delivery_fee', DECIMAL_VALUE_ZERO),
    ).annotate(
        total_amount=ExpressionWrapper(F('subtotal_amount') + F('delivery_fee_amount'), output_field=MONEY_FIELD)
    )


def validate_cart_inventory(cart_items):
    errors = []
    for item in cart_items:
        if item.product.inventory_locked:
            errors.append(
                f"{item.product.name} is currently locked by admin and cannot be ordered right now."
            )
            continue
        available_stock = item.product.stock
        if item.quantity > available_stock:
            errors.append(
                f"{item.product.name} only has {available_stock} item(s) left in stock."
            )
    return errors


@transaction.atomic
def reserve_inventory_for_order(order):
    if order.inventory_locked:
        return order

    order_items = list(order.items.select_related('product').select_for_update())
    if not order_items:
        raise ValidationError("This order has no items to reserve.")

    insufficient_stock = []
    for item in order_items:
        product = Product.objects.select_for_update().get(pk=item.product_id)
        if product.inventory_locked:
            insufficient_stock.append(f"{product.name} is currently locked by admin.")
            continue
        if item.quantity > product.stock:
            insufficient_stock.append(
                f"{product.name} only has {product.stock} item(s) left."
            )

    if insufficient_stock:
        raise ValidationError(insufficient_stock)

    for item in order_items:
        Product.objects.filter(pk=item.product_id).update(stock=F('stock') - item.quantity)

    order.inventory_locked = True
    if not order.current_location:
        order.current_location = get_status_location(order.status or 'Pending')
    order.save(update_fields=['inventory_locked', 'current_location', 'updated_at'])
    return order


@transaction.atomic
def release_inventory_for_order(order):
    if not order.inventory_locked:
        return order

    order_items = list(order.items.select_related('product').select_for_update())
    for item in order_items:
        Product.objects.filter(pk=item.product_id).update(stock=F('stock') + item.quantity)

    order.inventory_locked = False
    order.save(update_fields=['inventory_locked', 'updated_at'])
    return order


@transaction.atomic
def transition_order_status(order, new_status, updated_by=None, location=None, description=None):
    if new_status not in dict(Order.STATUS_CHOICES):
        raise ValidationError("Invalid order status.")

    previous_status = order.status or 'Pending'

    if previous_status != 'Cancelled' and new_status == 'Cancelled':
        release_inventory_for_order(order)
    elif previous_status == 'Cancelled' and new_status != 'Cancelled':
        reserve_inventory_for_order(order)

    order.status = new_status
    if new_status == 'Delivered':
        order.actual_delivery = order.actual_delivery or timezone.now()
        if order.payment_method == 'Cash on Delivery' and order.payment_status == 'Pending':
            order.payment_status = 'Paid'
    elif previous_status == 'Delivered' and new_status != 'Delivered':
        order.actual_delivery = None

    order.current_location = location or get_status_location(new_status)
    order.save()

    if description or previous_status != new_status or location:
        TrackingUpdate.objects.create(
            order=order,
            status=new_status,
            location=order.current_location,
            description=description or f'Status updated from {previous_status} to {new_status}.',
            updated_by=updated_by,
        )

    return order


def build_admin_dashboard(days=30):
    User = get_user_model()
    today = timezone.localdate()
    start_date = today - timedelta(days=days - 1) if days else None

    report_orders_qs = Order.objects.select_related('user')
    if start_date:
        report_orders_qs = report_orders_qs.filter(created_at__date__gte=start_date)

    report_orders = list(
        annotate_orders_with_totals(report_orders_qs)
        .prefetch_related(Prefetch('items', queryset=OrderItem.objects.select_related('product')))
        .order_by('-created_at')
    )

    all_recent_orders = list(
        annotate_orders_with_totals(
            Order.objects.select_related('user').prefetch_related(
                Prefetch('items', queryset=OrderItem.objects.select_related('product'))
            )
        ).order_by('-created_at')[:12]
    )

    sales_orders = [order for order in report_orders if order.status in NON_CANCELLED_STATUSES]
    delivered_orders = [order for order in report_orders if order.status == 'Delivered']
    open_orders = [order for order in report_orders if order.status in ['Pending', 'Processing', 'Shipped']]

    gross_sales = sum((order.total_amount for order in sales_orders), Decimal('0.00'))
    delivered_sales = sum((order.total_amount for order in delivered_orders), Decimal('0.00'))
    total_units_sold = sum((order.items_count for order in sales_orders), 0)

    active_products = Product.objects.filter(is_active=True)
    inventory_products = list(
        active_products.annotate(
            sold_quantity=Coalesce(
                Sum(
                    'orderitem__quantity',
                    filter=Q(orderitem__order__status__in=NON_CANCELLED_STATUSES),
                ),
                INTEGER_VALUE_ZERO,
            ),
            sales_revenue=Coalesce(
                Sum(
                    PRODUCT_LINE_TOTAL,
                    filter=Q(orderitem__order__status__in=NON_CANCELLED_STATUSES),
                ),
                DECIMAL_VALUE_ZERO,
            ),
        ).order_by('stock', 'name')
    )

    low_stock_products = [product for product in inventory_products if product.stock <= product.low_stock_threshold]
    out_of_stock_products = [product for product in inventory_products if product.stock == 0]
    inventory_units_remaining = sum((product.stock for product in inventory_products), 0)
    inventory_value = sum((product.price * product.stock for product in inventory_products), Decimal('0.00'))

    top_products = sorted(
        [product for product in inventory_products if product.sold_quantity],
        key=lambda product: (-product.sold_quantity, product.name.lower()),
    )[:8]
    sales_report_products = sorted(
        inventory_products,
        key=lambda product: (-product.sold_quantity, product.name.lower()),
    )
    stock_report_products = sorted(
        inventory_products,
        key=lambda product: (product.stock, product.name.lower()),
    )

    status_counter = Counter(order.status or 'Unknown' for order in report_orders)
    payment_counter = Counter(order.payment_method or 'Unknown' for order in report_orders)
    district_counter = Counter(order.district or 'Unassigned' for order in report_orders)

    if days:
        dates = [today - timedelta(days=offset) for offset in reversed(range(days))]
    else:
        oldest_date = min(
            (timezone.localtime(order.created_at).date() for order in report_orders if order.created_at),
            default=today,
        )
        span = max((today - oldest_date).days + 1, 1)
        dates = [oldest_date + timedelta(days=offset) for offset in range(span)]

    daily_sales = {
        current_date: {
            'date': current_date,
            'label': current_date.strftime('%b %d'),
            'order_count': 0,
            'revenue': Decimal('0.00'),
        }
        for current_date in dates
    }

    for order in sales_orders:
        if not order.created_at:
            continue
        order_date = timezone.localtime(order.created_at).date()
        if order_date in daily_sales:
            daily_sales[order_date]['order_count'] += 1
            daily_sales[order_date]['revenue'] += order.total_amount

    status_breakdown = [
        {'label': label, 'count': status_counter.get(label, 0)}
        for label, _ in Order.STATUS_CHOICES
    ]
    payment_breakdown = [
        {'label': label, 'count': count}
        for label, count in payment_counter.most_common()
    ]
    district_breakdown = [
        {'label': label, 'count': count}
        for label, count in district_counter.most_common()
    ]

    average_order_value = (
        gross_sales / Decimal(len(sales_orders))
        if sales_orders else Decimal('0.00')
    )

    registered_users = list(
        User.objects.order_by('-date_joined', 'username').only(
            'username',
            'first_name',
            'last_name',
            'email',
            'date_joined',
            'is_staff',
            'is_superuser',
        )
    )
    customer_accounts = [user for user in registered_users if not user.is_staff]
    recent_cancelled_orders = [order for order in all_recent_orders if order.status == 'Cancelled'][:6]

    return {
        'period_days': days,
        'period_label': f'Last {days} days' if days else 'All time',
        'metrics': {
            'orders_placed': len(report_orders),
            'open_orders': len(open_orders),
            'gross_sales': gross_sales,
            'delivered_sales': delivered_sales,
            'average_order_value': average_order_value,
            'units_sold': total_units_sold,
            'inventory_units_remaining': inventory_units_remaining,
            'inventory_value': inventory_value,
            'active_products': len(inventory_products),
            'low_stock_count': len(low_stock_products),
            'out_of_stock_count': len(out_of_stock_products),
            'registered_users': len(registered_users),
            'customer_accounts': len(customer_accounts),
        },
        'status_breakdown': status_breakdown,
        'payment_breakdown': payment_breakdown,
        'district_breakdown': district_breakdown,
        'daily_sales': list(daily_sales.values()),
        'top_products': top_products,
        'sales_report_products': sales_report_products,
        'stock_report_products': stock_report_products,
        'inventory_products': inventory_products[:12],
        'low_stock_products': low_stock_products[:8],
        'recent_orders': all_recent_orders,
        'recent_cancelled_orders': recent_cancelled_orders,
        'registered_users': registered_users,
        'recent_users': registered_users[:12],
    }
