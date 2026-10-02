from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.products.models import ProductVolume

from . import tests as ecommerce_tests
from .models import Cart, CartItem, Order, OrderPayment


class WhatsAppOrderTests(TestCase):
    setUp = ecommerce_tests.EcommerceFlowTests.setUp

    def product_review(self, **data):
        return self.client.get(reverse("orders:whatsapp_product", args=[self.product.uuid]), data)

    def guest_cart(self):
        session = self.client.session
        session.save()
        return Cart.objects.create(session_key=session.session_key)

    @override_settings(SITE_URL="https://jobellinc.com")
    def test_product_message_uses_discounted_prices_and_encoded_names(self):
        self.product.name = "Rose & Oud #1 / Édition"
        self.product.save()
        self.variant.discount_value = Decimal("20")
        self.variant.save()
        response = self.product_review(volume_id=self.variant.pk, quantity=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["subtotal"], Decimal("40"))
        message = parse_qs(urlsplit(response.context["whatsapp_url"]).query)["text"][0]
        self.assertIn(self.product.name, message)
        self.assertIn("Unit price: UGX 20", message)
        self.assertIn("Total: UGX 40", message)
        self.assertIn("*JOBELL STORE | ORDER ENQUIRY*", message)
        self.assertIn("*Subtotal: UGX 40*", message)
        self.assertIn("🔗 View product:\nhttps://jobellinc.com/orders/product/detail/", message)
        self.assertEqual(message, response.context["order_message"])
        self.assertContains(response, "Copy order message")

    @override_settings(SITE_URL="http://127.0.0.1:8000", BASE_DOMAIN="jobellinc.com")
    def test_local_review_shares_public_product_links(self):
        cart = self.guest_cart()
        CartItem.objects.create(cart=cart, product=self.product, volume=self.variant, quantity=2)
        response = self.client.get(reverse("orders:whatsapp_cart"))
        message = parse_qs(urlsplit(response.context["whatsapp_url"]).query)["text"][0]
        link = "https://jobellinc.com" + reverse("orders:product_detail", args=[self.product.uuid])
        self.assertIn(link, message.splitlines())
        self.assertNotIn("127.0.0.1", message)
        self.assertIn("Items: 2", message)

    def test_missing_variant_and_invalid_quantities_are_blocked(self):
        for data in ({}, {"volume_id": self.variant.pk, "quantity": "1.5"},
                     {"volume_id": self.variant.pk, "quantity": 0},
                     {"volume_id": self.variant.pk, "quantity": 4},
                     {"volume_id": 999999, "quantity": 1}):
            response = self.product_review(**data)
            self.assertTrue(response.context["errors"])
            self.assertNotContains(response, "Continue to WhatsApp ↗")

    def test_unavailable_products_and_stock_are_blocked(self):
        self.variant.stock_quantity = 0
        self.variant.save()
        self.assertTrue(self.product_review(volume_id=self.variant.pk, quantity=1).context["errors"])
        self.variant.stock_quantity = 5
        self.variant.is_active = False
        self.variant.save()
        self.assertTrue(self.product_review(volume_id=self.variant.pk, quantity=1).context["errors"])
        self.variant.is_active = True
        self.variant.save()
        self.product.status = "INACTIVE"
        self.product.save()
        self.assertTrue(self.product_review(volume_id=self.variant.pk, quantity=1).context["errors"])

    def test_empty_cart_does_not_create_items_or_order(self):
        response = self.client.get(reverse("orders:whatsapp_cart"))
        self.assertTrue(response.context["errors"])
        self.assertEqual(CartItem.objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)

    def test_multi_item_cart_and_repeated_review_do_not_mutate_state(self):
        cart = self.guest_cart()
        CartItem.objects.create(cart=cart, product=self.product, volume=self.variant, quantity=2)
        second = ProductVolume.objects.create(product=self.product, volume=self.volume, product_type="Spray", stock_quantity=4, price=Decimal("30"))
        CartItem.objects.create(cart=cart, product=self.product, volume=second, quantity=1)
        for _ in range(2):
            response = self.client.get(reverse("orders:whatsapp_cart"))
            self.assertEqual(len(response.context["lines"]), 2)
            self.assertEqual(response.context["subtotal"], Decimal("80"))
        self.variant.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 5)
        self.assertEqual(second.stock_quantity, 4)
        self.assertEqual(list(cart.items.order_by("id").values_list("quantity", flat=True)), [2, 1])
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderPayment.objects.count(), 0)

    def test_cart_stock_changes_block_whatsapp_link(self):
        cart = self.guest_cart()
        CartItem.objects.create(cart=cart, product=self.product, volume=self.variant, quantity=2)
        self.variant.stock_quantity = 1
        self.variant.save()
        response = self.client.get(reverse("orders:whatsapp_cart"))
        self.assertTrue(response.context["errors"])
        self.assertNotContains(response, "Continue to WhatsApp ↗")

    def test_authenticated_cart_is_used_without_exposing_another_cart(self):
        CartItem.objects.create(cart=Cart.objects.create(user=self.user), product=self.product, volume=self.variant, quantity=2)
        CartItem.objects.create(cart=Cart.objects.create(user=self.staff_user), product=self.product, volume=self.variant, quantity=3)
        self.client.force_login(self.user)
        response = self.client.get(reverse("orders:whatsapp_cart"))
        self.assertEqual(response.context["subtotal"], Decimal("50"))
        self.assertEqual(response.context["lines"][0]["quantity"], 2)

    def test_repeated_product_reviews_leave_stock_and_orders_unchanged(self):
        for _ in range(2):
            response = self.product_review(volume_id=self.variant.pk, quantity=1)
            self.assertFalse(response.context["errors"])
            self.assertIn("volume_id=", response.context["back_url"])
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 5)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderPayment.objects.count(), 0)
        self.assertEqual(CartItem.objects.count(), 0)
