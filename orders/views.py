import decimal
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from cart.models import Cart, CartItem
from products.models import Product

from .forms import OrderForm
from .models import Order, OrderItem, SMSNotification, TrackingUpdate
from .services import (
    annotate_orders_with_totals,
    build_admin_dashboard,
    get_status_location,
    reserve_inventory_for_order,
    transition_order_status,
    validate_cart_inventory,
)


def _get_order_for_user(user, order_id):
    queryset = Order.objects.select_related('user').prefetch_related('items__product', 'tracking_updates')
    if user.is_staff:
        return get_object_or_404(queryset, id=order_id)
    return get_object_or_404(queryset, id=order_id, user=user)


@login_required
def create_order(request):
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = list(CartItem.objects.select_related('product').filter(cart=cart))
    except Cart.DoesNotExist:
        cart = None
        cart_items = []

    if not cart_items:
        messages.warning(request, "Your cart is empty.")
        return redirect('cart_detail')

    stock_errors = validate_cart_inventory(cart_items)
    if stock_errors:
        for error in stock_errors:
            messages.error(request, error)
        return redirect('cart_detail')

    total = sum((item.product.price * item.quantity for item in cart_items), Decimal('0.00'))

    delivery_fee = Decimal('0.00') if total >= Decimal('50000.00') else Decimal('2000.00')

    if request.method == 'POST':
        form = OrderForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    locked_cart = Cart.objects.select_for_update().get(user=request.user)
                    locked_cart_items = list(
                        CartItem.objects.select_for_update().select_related('product').filter(cart=locked_cart)
                    )

                    if not locked_cart_items:
                        messages.warning(request, "Your cart is empty.")
                        return redirect('cart_detail')

                    stock_errors = validate_cart_inventory(locked_cart_items)
                    if stock_errors:
                        raise ValidationError(stock_errors)

                    order = form.save(commit=False)
                    order.user = request.user
                    if not order.email:
                        order.email = request.user.email
                    if not order.phone:
                        order.sms_opt_in = False
                    order.delivery_fee = delivery_fee
                    if not order.city:
                        order.city = 'Kigali'
                    order.estimated_delivery = timezone.now() + timedelta(hours=24)
                    order.current_location = get_status_location('Pending')
                    order.save()

                    OrderItem.objects.bulk_create([
                        OrderItem(
                            order=order,
                            product=item.product,
                            quantity=item.quantity,
                            price=item.product.price,
                        )
                        for item in locked_cart_items
                    ])

                    reserve_inventory_for_order(order)
                    TrackingUpdate.objects.create(
                        order=order,
                        status='Pending',
                        location=order.current_location,
                        description='Your order has been placed and stock has been reserved.',
                    )

                    CartItem.objects.filter(cart=locked_cart).delete()

                if order.sms_opt_in and order.phone:
                    print(f"SMS sent to {order.phone}: Order #{order.order_number} confirmed")

                messages.success(request, f"Order #{order.order_number} placed successfully.")
                return redirect('order_tracking', order_id=order.id)
            except ValidationError as exc:
                for error in exc.messages:
                    messages.error(request, error)
            except Cart.DoesNotExist:
                messages.error(request, "Your cart could not be found. Please try again.")
            except Exception:
                messages.error(request, "We couldn't place the order right now. Please try again.")
    else:
        initial_data = {
            'full_name': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
            'sms_opt_in': True,
        }
        form = OrderForm(initial=initial_data)

    return render(request, 'checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'total': total,
        'delivery_fee': delivery_fee,
        'grand_total': total + delivery_fee,
    })


@login_required
def my_orders(request):
    orders = list(
        annotate_orders_with_totals(
            Order.objects.filter(user=request.user).prefetch_related('items__product')
        )
    )

    total_orders = len(orders)
    delivered_orders = sum(1 for order in orders if order.status == 'Delivered')
    pending_orders = sum(1 for order in orders if order.status == 'Pending')
    processing_orders = sum(1 for order in orders if order.status == 'Processing')
    shipped_orders = sum(1 for order in orders if order.status == 'Shipped')
    cancelled_orders = sum(1 for order in orders if order.status == 'Cancelled')
    total_spent = sum((order.total_amount for order in orders if order.status != 'Cancelled'), Decimal('0.00'))

    return render(request, 'my_orders.html', {
        'orders': orders,
        'total_orders': total_orders,
        'delivered_orders': delivered_orders,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'shipped_orders': shipped_orders,
        'cancelled_orders': cancelled_orders,
        'total_spent': total_spent,
    })


@login_required
def invoice(request, order_id):
    order = _get_order_for_user(request.user, order_id)
    items = OrderItem.objects.filter(order=order).select_related('product')
    auto_print = request.GET.get('print') == '1'

    return render(request, 'invoice.html', {
        'order': order,
        'items': items,
        'auto_print': auto_print,
    })


@login_required
def order_tracking(request, order_id):
    order = _get_order_for_user(request.user, order_id)
    tracking_updates = order.get_tracking_history()
    auto_print = request.GET.get('print') == '1'

    return render(request, 'order_tracking.html', {
        'order': order,
        'tracking_updates': tracking_updates,
        'progress': order.get_status_percentage(),
        'estimated_delivery': order.estimated_delivery,
        'auto_print': auto_print,
    })


def public_tracking_search(request):
    tracking_number = request.GET.get('tracking_number', '').strip().upper()
    order = None
    tracking_error = None

    if tracking_number:
        compact_value = ''.join(tracking_number.split())
        candidates = {tracking_number, compact_value}

        if compact_value.startswith('TRK') and not compact_value.startswith('TRK-'):
            candidates.add(f"TRK-{compact_value[3:]}")
        if compact_value.startswith('EMG') and not compact_value.startswith('EMG-'):
            candidates.add(f"EMG-{compact_value[3:]}")

        query = Q()
        for candidate in candidates:
            query |= Q(tracking_number__iexact=candidate) | Q(order_number__iexact=candidate)

        match = Order.objects.filter(query).first()
        if match:
            return redirect('public_tracking', tracking_number=match.tracking_number)
        tracking_error = "We couldn't find an order with that tracking or order number."

    return render(request, 'public_tracking.html', {
        'order': order,
        'tracking_updates': [],
        'progress': 0,
        'tracking_number': tracking_number,
        'tracking_error': tracking_error,
    })


def public_tracking(request, tracking_number):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'tracking_updates__updated_by'),
        tracking_number=tracking_number,
    )
    tracking_updates = list(order.get_tracking_history())
    latest_update = tracking_updates[0] if tracking_updates else None

    return render(request, 'public_tracking.html', {
        'order': order,
        'tracking_updates': tracking_updates,
        'progress': order.get_status_percentage(),
        'tracking_number': tracking_number,
        'latest_update': latest_update,
    })


@login_required
def cancel_order(request, order_id):
    order = _get_order_for_user(request.user, order_id)

    if order.can_cancel():
        transition_order_status(
            order,
            'Cancelled',
            updated_by=request.user if request.user.is_staff else None,
            description='Order has been cancelled by the customer.',
        )
        SMSNotification.objects.create(
            order=order,
            phone_number='ADMIN',
            message=f'Admin alert: Order {order.order_number} was cancelled by {order.full_name or request.user.username}.',
            type='status_update',
            status='sent',
            provider_response='Internal admin notification',
            sent_at=timezone.now(),
        )
        messages.success(request, f"Order #{order.order_number} cancelled successfully.")
    else:
        messages.error(request, "Only pending or processing orders can be cancelled.")

    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('my_orders')


@login_required
def reorder(request, order_id):
    old_order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id, user=request.user)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    old_items = old_order.items.select_related('product')

    if not old_items:
        messages.warning(request, "No items found in this order.")
        return redirect('my_orders')

    added_products = 0
    for old_item in old_items:
        product = old_item.product
        if not product or not product.is_active or product.stock <= 0:
            messages.warning(request, f"{product.name if product else 'This product'} is currently unavailable.")
            continue

        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': 0})
        desired_quantity = cart_item.quantity + old_item.quantity
        final_quantity = min(desired_quantity, product.stock)

        if final_quantity == cart_item.quantity:
            messages.warning(request, f"{product.name} could not be added because it is out of stock.")
            continue

        cart_item.quantity = final_quantity
        cart_item.save()
        added_products += 1

        if final_quantity < desired_quantity:
            messages.info(request, f"{product.name} was limited to the available stock of {product.stock}.")

    if added_products:
        messages.success(request, "Selected items were added back to your cart.")
    return redirect('cart_detail')


@staff_member_required(login_url='login')
def admin_dashboard(request):
    allowed_periods = {7, 30, 90}
    try:
        period = int(request.GET.get('period', 30))
    except ValueError:
        period = 30

    if period not in allowed_periods:
        period = 30

    context = build_admin_dashboard(period)
    context['status_choices'] = Order.STATUS_CHOICES
    return render(request, 'admin_dashboard.html', context)


@staff_member_required(login_url='login')
def inventory_management(request):
    if request.method == 'POST':
        action = (request.POST.get('action') or '').strip()
        product_id = request.POST.get('product_id')

        if action == 'create':
            name = (request.POST.get('name') or '').strip()
            category = (request.POST.get('category') or '').strip()
            description = (request.POST.get('description') or '').strip()

            if not name or not description:
                messages.error(request, 'Name and description are required to create inventory.')
                return redirect('inventory_management')

            if category not in dict(Product.CATEGORY_CHOICES):
                category = Product.CATEGORY_GENERAL

            try:
                price = Decimal(request.POST.get('price', '0'))
                stock = int(request.POST.get('stock', 0))
                low_stock_threshold = int(request.POST.get('low_stock_threshold', 5))
            except (TypeError, ValueError, decimal.InvalidOperation):
                messages.error(request, 'Invalid values provided for the new product.')
                return redirect('inventory_management')

            product = Product.objects.create(
                name=name,
                category=category,
                description=description,
                price=price,
                stock=stock,
                low_stock_threshold=low_stock_threshold,
                inventory_locked=request.POST.get('inventory_locked') == 'on',
                is_active=request.POST.get('is_active') == 'on',
            )
            messages.success(request, f'{product.name} added to inventory successfully.')
            return redirect('inventory_management')

        if action == 'unlock_all':
            updated = Product.objects.filter(inventory_locked=True).update(inventory_locked=False)
            messages.success(request, f'{updated} product(s) unlocked.')
            return redirect('inventory_management')

        product = get_object_or_404(Product, id=product_id) if product_id else None

        if action == 'update' and product:
            product.name = request.POST.get('name', product.name).strip() or product.name
            category = request.POST.get('category', product.category).strip()
            if category in dict(Product.CATEGORY_CHOICES):
                product.category = category
            product.description = request.POST.get('description', product.description).strip() or product.description

            try:
                product.price = Decimal(request.POST.get('price', product.price))
                product.stock = int(request.POST.get('stock', product.stock))
                product.low_stock_threshold = int(request.POST.get('low_stock_threshold', product.low_stock_threshold))
            except (TypeError, ValueError, decimal.InvalidOperation):
                messages.error(request, f'Invalid inventory values for {product.name}.')
                return redirect('inventory_management')

            product.is_active = request.POST.get('is_active') == 'on'
            product.inventory_locked = request.POST.get('inventory_locked') == 'on'
            product.save()
            messages.success(request, f'{product.name} updated successfully.')
            return redirect('inventory_management')

        if action == 'delete' and product:
            product_name = product.name
            product.delete()
            messages.success(request, f'{product_name} deleted successfully.')
            return redirect('inventory_management')

        if action == 'toggle_lock' and product:
            product.inventory_locked = not product.inventory_locked
            product.save(update_fields=['inventory_locked', 'updated_at'])
            state = 'locked' if product.inventory_locked else 'unlocked'
            messages.success(request, f'{product.name} {state} successfully.')
            return redirect('inventory_management')

        messages.error(request, 'Inventory action could not be completed.')
        return redirect('inventory_management')

    products = Product.objects.order_by('name')
    return render(request, 'inventory_management.html', {
        'products': products,
        'category_choices': Product.CATEGORY_CHOICES,
    })


@staff_member_required(login_url='login')
def admin_order_status_update(request, order_id):
    if request.method != 'POST':
        return redirect('admin_dashboard')

    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)
    new_status = request.POST.get('status', '').strip()
    location = request.POST.get('location', '').strip()
    description = request.POST.get('description', '').strip()
    next_url = request.POST.get('next') or 'admin_dashboard'

    try:
        transition_order_status(
            order,
            new_status,
            updated_by=request.user,
            location=location or None,
            description=description or None,
        )
        messages.success(request, f"Order #{order.order_number} updated to {new_status}.")
    except ValidationError as exc:
        for error in exc.messages:
            messages.error(request, error)

    return redirect(next_url)


@login_required
@csrf_exempt
def update_order_status(request, order_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)

    try:
        data = json.loads(request.body)
        transition_order_status(
            order,
            data.get('status'),
            updated_by=request.user,
            location=data.get('location') or None,
            description=data.get('description') or None,
        )
        return JsonResponse({'success': True, 'message': f'Order status updated to {order.status}.'})
    except (json.JSONDecodeError, ValidationError) as exc:
        message = exc.messages if hasattr(exc, 'messages') else [str(exc)]
        return JsonResponse({'error': ' '.join(message)}, status=400)


@login_required
def get_order_stats(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        period = int(request.GET.get('period', 30))
    except ValueError:
        period = 30

    dashboard = build_admin_dashboard(period if period in {7, 30, 90} else 30)
    return JsonResponse({
        'success': True,
        'period_label': dashboard['period_label'],
        'metrics': {
            key: float(value) if isinstance(value, Decimal) else value
            for key, value in dashboard['metrics'].items()
        },
        'status_breakdown': dashboard['status_breakdown'],
        'payment_breakdown': dashboard['payment_breakdown'],
        'district_breakdown': dashboard['district_breakdown'],
        'daily_sales': [
            {
                'date': entry['date'].isoformat(),
                'label': entry['label'],
                'order_count': entry['order_count'],
                'revenue': float(entry['revenue']),
            }
            for entry in dashboard['daily_sales']
        ],
    })


@login_required
def get_tracking_data(request, order_id):
    order = _get_order_for_user(request.user, order_id)
    tracking_updates = order.get_tracking_history()

    data = {
        'order_number': order.order_number,
        'status': order.status,
        'status_percentage': order.get_status_percentage(),
        'estimated_delivery': order.estimated_delivery.isoformat() if order.estimated_delivery else None,
        'actual_delivery': order.actual_delivery.isoformat() if order.actual_delivery else None,
        'current_location': order.current_location,
        'tracking_updates': [
            {
                'status': update.status,
                'location': update.location,
                'description': update.description,
                'time': update.created_at.isoformat() if update.created_at else None,
                'formatted_time': update.created_at.strftime('%b %d, %Y at %H:%M') if update.created_at else 'Unknown',
            }
            for update in tracking_updates[:10]
        ],
    }

    return JsonResponse(data)
