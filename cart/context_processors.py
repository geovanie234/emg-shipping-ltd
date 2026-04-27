from .models import Cart, CartItem
from django.db.models import Sum

def cart_count(request):
    """Add cart count to all templates"""
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            count = CartItem.objects.filter(cart=cart).aggregate(total=Sum('quantity'))['total'] or 0
            return {'cart_count': count}
        except Cart.DoesNotExist:
            return {'cart_count': 0}
    return {'cart_count': 0}
