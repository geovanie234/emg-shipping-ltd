from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from products.models import Product
from .models import Cart, CartItem
from decimal import Decimal

@login_required
def cart_detail(request):
    """Display shopping cart - requires login"""
    # Get or create cart for the logged-in user
    cart, created = Cart.objects.get_or_create(user=request.user)
    items = CartItem.objects.filter(cart=cart)
    
    # Calculate total price
    subtotal = sum((item.total_price() for item in items), Decimal('0.00'))
    delivery_fee = Decimal('0.00') if subtotal >= Decimal('50000.00') else Decimal('2000.00')
    grand_total = subtotal + delivery_fee
    
    context = {
        'items': items,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'grand_total': grand_total,
        'cart_count': items.count()
    }
    return render(request, 'cart.html', context)


@login_required
def add_to_cart(request, product_id):
    """Add product to cart - requires login"""
    # Get product or return 404
    product = get_object_or_404(Product, id=product_id, is_active=True)

    if product.inventory_locked:
        messages.error(request, f"{product.name} is currently locked and cannot be ordered.")
        return redirect('product_detail', id=product_id)
    
    # Check if product is in stock
    if product.stock <= 0:
        messages.error(request, f"Sorry, {product.name} is out of stock!")
        return redirect('product_detail', id=product_id)
    
    # Get or create cart for the user
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Get or create cart item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )
    
    # If item already exists, increase quantity
    if not created:
        # Check if adding one more exceeds stock
        if cart_item.quantity + 1 > product.stock:
            messages.warning(request, f"Only {product.stock} {product.name}(s) available in stock!")
            return redirect('cart_detail')
        
        cart_item.quantity += 1
        cart_item.save()
        messages.success(request, f"Added another {product.name} to your cart! (Now {cart_item.quantity} items)")
    else:
        messages.success(request, f"{product.name} added to your cart!")
    
    return redirect('cart_detail')


@login_required
def update_cart_item(request, item_id):
    """Update cart item quantity - requires login"""
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = int(request.POST.get('quantity', 1))
        
        # Validate quantity
        if quantity < 1:
            product_name = cart_item.product.name
            cart_item.delete()
            messages.success(request, f"{product_name} removed from cart!")
        elif cart_item.product.inventory_locked:
            messages.warning(request, f"{cart_item.product.name} is locked and cannot be updated right now.")
        elif quantity > cart_item.product.stock:
            messages.warning(request, f"Only {cart_item.product.stock} {cart_item.product.name}(s) available!")
        else:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, f"{cart_item.product.name} quantity updated to {quantity}!")
    
    return redirect('cart_detail')


@login_required
def remove_cart_item(request, item_id):
    """Remove item from cart - requires login"""
    if request.method == 'POST':
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        product_name = cart_item.product.name
        cart_item.delete()
        messages.success(request, f"{product_name} removed from cart!")
    
    return redirect('cart_detail')


@login_required
def clear_cart(request):
    """Clear all items from cart - requires login"""
    if request.method == 'POST':
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_items = CartItem.objects.filter(cart=cart)
            item_count = cart_items.count()
            cart_items.delete()
            messages.success(request, f"Cart cleared! {item_count} item(s) removed.")
    
    return redirect('cart_detail')
