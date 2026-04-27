from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Cart, CartItem
from products.models import Product


class CartCheckoutNavigationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cart-user', password='secret123')
        self.product = Product.objects.create(
            name='Cart Product',
            description='Product used to verify cart checkout navigation',
            price=Decimal('5000.00'),
            stock=10,
        )
        self.cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=1)

    def test_cart_page_contains_checkout_form_action(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('cart_detail'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'action="{reverse("checkout")}"')
        self.assertContains(response, 'Proceed to Checkout')

    def test_checkout_page_opens_from_cart_flow(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('checkout'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Secure Checkout')

    def test_locked_product_cannot_be_added_to_cart(self):
        locked_product = Product.objects.create(
            name='Locked Product',
            description='Locked for inventory management',
            price=Decimal('3000.00'),
            stock=7,
            inventory_locked=True,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('add_to_cart', args=[locked_product.id]), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'currently locked and cannot be ordered')
        self.assertFalse(CartItem.objects.filter(cart=self.cart, product=locked_product).exists())
