from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from . import tests as ecommerce_tests
from .models import Cart, CartItem
from .models import Order
from apps.shipping.models import PickupStation
from django.test import Client


class CartPageTests(TestCase):
    setUp = ecommerce_tests.EcommerceFlowTests.setUp

    def item(self):
        self.client.force_login(self.user)
        return CartItem.objects.create(cart=Cart.objects.get_or_create(user=self.user, session_key=None)[0], product=self.product, volume=self.variant, quantity=1)

    def test_empty_and_populated_layout(self):
        self.assertContains(self.client.get(reverse('orders:cart')), 'Your cart is empty')
        item = self.item()
        response = self.client.get(reverse('orders:cart'))
        self.assertContains(response, 'cart.css')
        self.assertContains(response, 'data-step="1"')
        self.assertEqual(response.context['cart_items'][0].quantity_limit, 3)
        self.assertContains(response, 'Continue to checkout')
        self.assertContains(response, 'commerce-dock')
        self.assertContains(response, 'commerce-cart-progress')
        self.assertContains(response, 'commerce-app commerce-cart')

    def test_checkout_has_mobile_progress_and_final_review(self):
        self.item()
        response = self.client.get(reverse('orders:checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-checkout-step="3"')
        self.assertContains(response, 'id="mobileCheckoutAction"')
        self.assertContains(response, 'commerce_mobile.js')
        self.assertContains(response, 'id="placeOrderBtn"')

    def test_guest_checkout_can_place_order_and_confirmation_is_private(self):
        session = self.client.session
        session.save()
        cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=cart, product=self.product, volume=self.variant, quantity=1)
        self.assertEqual(self.client.get(reverse('orders:checkout')).status_code, 200)
        station = PickupStation.objects.create(name='Test pickup', city='Kampala', area='Central', address='Test address')
        response = self.client.post(reverse('orders:checkout'), {'first_name':'Guest', 'mobile':'0701234567', 'shipping_method':'pickup', 'pickup_station':station.pk, 'payment_method':'cod'})
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get()
        self.assertIsNone(order.customer.user_id)
        self.assertEqual(order.payment_status, 'pending')
        url = reverse('orders:order_confirmation', args=[order.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(Client().get(url).status_code, 302)
        self.assertEqual(self.client.post(reverse('orders:checkout'), {'first_name':'Guest'}).status_code, 302)
        self.assertEqual(Order.objects.count(), 1)

    def test_invalid_quantity_keeps_item(self):
        item = self.item()
        for quantity in ('abc', '1.5', '0', '-1', '4', '999'):
            response = self.client.post(reverse('orders:update_cart', args=[item.pk]), {'quantity': quantity})
            self.assertEqual(response.status_code, 302)
            item.refresh_from_db()
            self.assertEqual(item.quantity, 1)

    def test_update_and_remove_require_post(self):
        item = self.item()
        for name in ('update_cart', 'remove_from_cart'):
            self.assertEqual(self.client.get(reverse('orders:' + name, args=[item.pk])).status_code, 405)
        self.client.post(reverse('orders:update_cart', args=[item.pk]), {'quantity': 2})
        response = self.client.get(reverse('orders:cart'))
        self.assertEqual(response.context['total_price'], Decimal('50'))
        self.client.post(reverse('orders:remove_from_cart', args=[item.pk]))
        self.assertFalse(CartItem.objects.filter(pk=item.pk).exists())

    def test_stock_changes_show_actionable_notice(self):
        self.item()
        self.variant.stock_quantity = 0
        self.variant.save()
        response = self.client.get(reverse('orders:cart'))
        self.assertTrue(response.context['cart_needs_attention'])
        self.assertContains(response, 'Check your items to continue')
        self.assertNotContains(response, 'data-cart-continue')

    def test_cannot_change_another_users_cart(self):
        item = self.item()
        self.client.force_login(self.staff_user)
        for name in ('update_cart', 'remove_from_cart'):
            self.assertEqual(self.client.post(reverse('orders:' + name, args=[item.pk]), {'quantity': 2}).status_code, 404)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)
