from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from cart.models import Cart, CartItem
from orders.models import Order, OrderItem, SMSNotification, TrackingUpdate
from products.models import Product


class OrderInventoryFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='customer', password='secret123')
        self.product = Product.objects.create(
            name='Wireless Headphones',
            description='Noise cancelling headphones',
            price=Decimal('15000.00'),
            stock=10,
        )
        self.cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)

    def test_checkout_reserves_stock_and_persists_order_details(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('checkout'), {
            'full_name': 'Test Customer',
            'email': 'customer@example.com',
            'phone': '0788123456',
            'address': 'KG 123 St',
            'district': 'Gasabo',
            'payment_method': 'Cash on Delivery',
            'sms_opt_in': 'on',
            'notes': 'Leave at the reception desk.',
        })

        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(user=self.user)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)
        self.assertTrue(order.inventory_locked)
        self.assertEqual(order.notes, 'Leave at the reception desk.')
        self.assertTrue(order.sms_opt_in)
        self.assertEqual(order.current_location, 'Order Processing Center')
        self.assertTrue(OrderItem.objects.filter(order=order, product=self.product, quantity=2).exists())
        self.assertTrue(TrackingUpdate.objects.filter(order=order, status='Pending').exists())
        self.assertFalse(CartItem.objects.filter(cart=self.cart).exists())

    def test_checkout_applies_free_delivery_for_large_orders(self):
        expensive_product = Product.objects.create(
            name='Large Appliance',
            description='Expensive item for free delivery threshold',
            price=Decimal('60000.00'),
            stock=3,
        )
        CartItem.objects.all().delete()
        CartItem.objects.create(cart=self.cart, product=expensive_product, quantity=1)

        self.client.force_login(self.user)
        response = self.client.post(reverse('checkout'), {
            'full_name': 'Test Customer',
            'email': 'customer@example.com',
            'phone': '0788 123 456',
            'address': 'KG 123 St',
            'district': 'Gasabo',
            'payment_method': 'Cash on Delivery',
            'sms_opt_in': 'on',
            'notes': '',
        })

        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(user=self.user)
        self.assertEqual(order.delivery_fee, Decimal('0.00'))
        self.assertEqual(order.phone, '0788123456')

    def test_checkout_allows_blank_phone_number(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('checkout'), {
            'full_name': 'Test Customer',
            'email': 'customer@example.com',
            'phone': '',
            'address': 'KG 123 St',
            'district': 'Gasabo',
            'payment_method': 'Cash on Delivery',
            'sms_opt_in': 'on',
            'notes': '',
        })

        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(user=self.user)
        self.assertFalse(order.phone)
        self.assertFalse(order.sms_opt_in)

    def test_cancelling_order_restores_inventory(self):
        self.client.force_login(self.user)
        self.client.post(reverse('checkout'), {
            'full_name': 'Test Customer',
            'email': 'customer@example.com',
            'phone': '0788123456',
            'address': 'KG 123 St',
            'district': 'Gasabo',
            'payment_method': 'Cash on Delivery',
            'sms_opt_in': 'on',
            'notes': '',
        })

        order = Order.objects.get(user=self.user)
        response = self.client.get(reverse('cancel_order', args=[order.id]))

        self.assertEqual(response.status_code, 302)
        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(order.status, 'Cancelled')
        self.assertFalse(order.inventory_locked)
        self.assertEqual(self.product.stock, 10)
        self.assertTrue(
            SMSNotification.objects.filter(order=order, phone_number='ADMIN', type='status_update').exists()
        )

    def test_checkout_rejects_short_phone_numbers(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('checkout'), {
            'full_name': 'Test Customer',
            'email': 'customer@example.com',
            'phone': '0789',
            'address': 'KG 123 St',
            'district': 'Gasabo',
            'payment_method': 'Cash on Delivery',
            'sms_opt_in': 'on',
            'notes': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter a valid phone number with at least 10 digits.')
        self.assertFalse(Order.objects.filter(user=self.user, phone='0789').exists())

    def test_checkout_rejects_locked_inventory_products(self):
        self.product.inventory_locked = True
        self.product.save(update_fields=['inventory_locked'])
        self.client.force_login(self.user)

        response = self.client.post(reverse('checkout'), {
            'full_name': 'Test Customer',
            'email': 'customer@example.com',
            'phone': '0788123456',
            'address': 'KG 123 St',
            'district': 'Gasabo',
            'payment_method': 'Cash on Delivery',
            'sms_opt_in': 'on',
            'notes': '',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'currently locked by admin')
        self.assertFalse(Order.objects.filter(user=self.user, items__product=self.product).exists())


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username='admin', password='secret123', is_staff=True)
        self.customer = User.objects.create_user(username='buyer', password='secret123')
        self.product = Product.objects.create(
            name='Smart Watch',
            description='Fitness tracking watch',
            price=Decimal('25000.00'),
            stock=6,
            low_stock_threshold=3,
        )
        self.order = Order.objects.create(
            user=self.customer,
            full_name='Buyer One',
            phone='0788000000',
            address='KN 1',
            district='Kicukiro',
            payment_method='Cash on Delivery',
            status='Pending',
            inventory_locked=True,
        )
        OrderItem.objects.create(order=self.order, product=self.product, quantity=2, price=self.product.price)

    def test_staff_can_view_admin_dashboard(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inventory and sales reporting')
        self.assertContains(response, f'{reverse("admin_dashboard")}#reports')
        self.assertContains(response, 'Sales by Item')
        self.assertContains(response, 'Remaining Stock Report')
        self.assertContains(response, self.product.name)
        self.assertContains(response, self.order.order_number)
        self.assertContains(response, 'total users')
        self.assertContains(response, self.customer.username)

    def test_non_staff_cannot_view_admin_dashboard(self):
        self.client.force_login(self.customer)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 302)

    def test_admin_dashboard_contains_invoice_and_print_links(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('invoice', args=[self.order.id]))
        self.assertContains(response, f"{reverse('invoice', args=[self.order.id])}?print=1")

    def test_staff_can_cancel_customer_order_from_tracking_flow(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(
            f"{reverse('cancel_order', args=[self.order.id])}?next={reverse('order_tracking', args=[self.order.id])}"
        )

        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'Cancelled')


class InventoryManagementTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username='stock-admin', password='secret123', is_staff=True)
        self.customer = User.objects.create_user(username='stock-customer', password='secret123')
        self.product = Product.objects.create(
            name='Inventory Item',
            description='Inventory management test item',
            price=Decimal('12000.00'),
            stock=9,
            low_stock_threshold=2,
        )

    def test_staff_can_open_inventory_management_page(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse('inventory_management'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Manage products, stock, and lock status')
        self.assertContains(response, self.product.name)

    def test_non_staff_cannot_open_inventory_management_page(self):
        self.client.force_login(self.customer)

        response = self.client.get(reverse('inventory_management'))

        self.assertEqual(response.status_code, 302)

    def test_staff_can_update_and_lock_inventory_item(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(reverse('inventory_management'), {
            'action': 'update',
            'product_id': self.product.id,
            'name': 'Updated Inventory Item',
            'category': self.product.category,
            'description': 'Updated description',
            'price': '15000.00',
            'stock': '4',
            'low_stock_threshold': '1',
            'inventory_locked': 'on',
            'is_active': 'on',
        })

        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Inventory Item')
        self.assertEqual(self.product.stock, 4)
        self.assertTrue(self.product.inventory_locked)

    def test_staff_can_delete_inventory_item(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(reverse('inventory_management'), {
            'action': 'delete',
            'product_id': self.product.id,
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'deleted successfully')
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())

    def test_staff_can_create_inventory_item(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(reverse('inventory_management'), {
            'action': 'create',
            'name': 'Created Inventory Item',
            'category': Product.CATEGORY_GENERAL,
            'description': 'Created through staff inventory page',
            'price': '22000.00',
            'stock': '12',
            'low_stock_threshold': '3',
            'is_active': 'on',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'added to inventory successfully')
        self.assertTrue(Product.objects.filter(name='Created Inventory Item', stock=12).exists())

    def test_staff_can_toggle_lock_inventory_item_and_see_notification(self):
        self.client.force_login(self.staff_user)

        response = self.client.post(reverse('inventory_management'), {
            'action': 'toggle_lock',
            'product_id': self.product.id,
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertTrue(self.product.inventory_locked)
        self.assertContains(response, 'locked successfully')

        response = self.client.post(reverse('inventory_management'), {
            'action': 'toggle_lock',
            'product_id': self.product.id,
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertFalse(self.product.inventory_locked)
        self.assertContains(response, 'unlocked successfully')


class PublicTrackingSearchTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tracking-user', password='secret123')
        self.order = Order.objects.create(
            user=self.user,
            full_name='Tracking Customer',
            phone='0788123456',
            address='KG 11 Ave',
            district='Gasabo',
            payment_method='Cash on Delivery',
            payment_status='Pending',
            status='Processing',
            current_location='Warehouse',
        )

    def test_public_tracking_search_accepts_tracking_number(self):
        response = self.client.get(reverse('public_tracking_search'), {'tracking_number': self.order.tracking_number})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('public_tracking', args=[self.order.tracking_number]))

    def test_public_tracking_search_accepts_order_number(self):
        response = self.client.get(reverse('public_tracking_search'), {'tracking_number': self.order.order_number})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('public_tracking', args=[self.order.tracking_number]))

    def test_public_tracking_search_accepts_order_number_without_hyphen(self):
        compact_order_number = self.order.order_number.replace('-', '')

        response = self.client.get(reverse('public_tracking_search'), {'tracking_number': compact_order_number})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('public_tracking', args=[self.order.tracking_number]))

    def test_public_tracking_search_accepts_tracking_number_with_extra_spaces(self):
        spaced_tracking_number = f"  {self.order.tracking_number.replace('-', ' - ')}  "

        response = self.client.get(reverse('public_tracking_search'), {'tracking_number': spaced_tracking_number})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('public_tracking', args=[self.order.tracking_number]))

    def test_public_tracking_page_shows_cancel_link_for_owner(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('public_tracking', args=[self.order.tracking_number]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cancel Order')


class InvoicePrintTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='invoice-user', password='secret123')
        self.product = Product.objects.create(
            name='Invoice Product',
            description='Invoice printing product',
            price=Decimal('10000.00'),
            stock=5,
        )
        self.order = Order.objects.create(
            user=self.user,
            full_name='Invoice Customer',
            phone='0788123456',
            address='KG 10 Ave',
            district='Gasabo',
            payment_method='Cash on Delivery',
            status='Pending',
        )
        OrderItem.objects.create(order=self.order, product=self.product, quantity=1, price=self.product.price)

    def test_invoice_page_renders_print_button(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('invoice', args=[self.order.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Print Invoice')

    def test_invoice_page_supports_auto_print_mode(self):
        self.client.force_login(self.user)

        response = self.client.get(f"{reverse('invoice', args=[self.order.id])}?print=1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'window.print()')

    def test_order_tracking_page_supports_auto_print_mode(self):
        self.client.force_login(self.user)

        response = self.client.get(f"{reverse('order_tracking', args=[self.order.id])}?print=1")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'window.print()')
