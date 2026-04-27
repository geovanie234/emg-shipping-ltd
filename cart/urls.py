from django.urls import path
from . import views

urlpatterns = [
    # Display shopping cart
    path('', views.cart_detail, name='cart_detail'),
    
    # Add product to cart (requires product ID)
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    
    # Update cart item quantity (requires cart item ID)
    path('update/<int:item_id>/', views.update_cart_item, name='update_cart'),
    
    # Remove item from cart (requires cart item ID)
    path('remove/<int:item_id>/', views.remove_cart_item, name='remove_cart'),
    
    # Clear entire cart
    path('clear/', views.clear_cart, name='clear_cart'),
]