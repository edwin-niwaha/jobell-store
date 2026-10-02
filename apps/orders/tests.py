from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.db import IntegrityError
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.addresses.models import CustomerAddress
from apps.authentication.models import Profile
from apps.customers.models import Customer
from apps.orders.forms import CheckoutForm
from apps.orders.models import (
    Cart,
    CartItem,
    Order,
    OrderDetail,
    OrderPayment,
    Wishlist,
)
from apps.orders.notifications import (
    _order_context,
    queue_order_status_changed_emails,
    queue_payment_status_changed_emails,
)
from apps.orders.services import (
    cart_total,
    create_order_from_cart,
    mark_order_paid_and_capture_sale,
)
from apps.products.models import Category, Product, ProductVolume, Volume
from apps.sales.models import Sale, SaleDetail
from apps.shipping.models import DeliveryRate, PickupStation
from apps.shipping.services import delivery_quote_for
from apps.supplier.models import Supplier
from core.services.email_service import EmailServiceError


class EcommerceFlowTests(TestCase):
    def test_storefront_wishlist_hearts_are_personal_and_duplicate_add_shows_message(self):
        Wishlist.objects.create(user=self.user, product=self.product)
        urls = [reverse("users-home"), reverse("products:shop_homepage")]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.context["wishlist_product_ids"], set())
            self.assertNotContains(response, 'aria-pressed="true"')
        self.client.force_login(self.user)
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.context["wishlist_product_ids"], {self.product.pk})
            self.assertContains(response, 'aria-pressed="true"')
        response = self.client.post(reverse("orders:wishlist_add", args=[self.product.uuid]),
                                    {"next": urls[1]}, follow=True)
        self.assertContains(response, "already in your wishlist")
        self.assertEqual(Wishlist.objects.filter(user=self.user, product=self.product).count(), 1)
        self.client.force_login(self.staff_user)
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.context["wishlist_product_ids"], set())
            self.assertNotContains(response, 'aria-pressed="true"')

    def test_product_detail_explains_unavailable_inventory_without_purchase_form(self):
        self.variant.stock_quantity = None
        self.variant.save()
        response = self.client.get(reverse("orders:product_detail", args=[self.product.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This fragrance is currently unavailable.")
        self.assertContains(response, "Save to wishlist")
        self.assertNotContains(response, 'id="add-to-cart-form"')
        self.assertEqual(response.context["product_volumes"], [])

    def test_product_detail_shows_price_and_sellable_purchase_options(self):
        response = self.client.get(reverse("orders:product_detail", args=[self.product.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="selected-price">UGX 25')
        self.assertContains(response, 'id="add-to-cart-form"')
        self.assertContains(response, "In stock")
        self.assertEqual(response.context["product_volumes"], [self.variant])

    def test_storefront_filters_use_discounted_variant_prices(self):
        self.variant.price = Decimal("100")
        self.variant.discount_value = Decimal("50")
        self.variant.save()
        response = self.client.get(reverse("products:shop_homepage"), {"min_price": "45", "max_price": "55", "sort": "price_asc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result_count"], 1)
        self.assertEqual(response.context["products_with_images"][0]["min_price"], Decimal("50"))
        response = self.client.get(reverse("products:shop_homepage"), {"min_price": "60"})
        self.assertEqual(response.context["result_count"], 0)

    def test_storefront_preserves_encoded_filters(self):
        response = self.client.get(reverse("products:shop_homepage"), {"search": "Citrus & Rose", "min_price": "10", "sort": "price_desc", "page": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("search=Citrus+%26+Rose", response.context["filter_query"])
        self.assertIn("min_price=10", response.context["filter_query"])
        self.assertNotIn("page=", response.context["filter_query"])

    def test_home_new_arrivals_include_new_nonfeatured_products(self):
        self.product.is_featured = True
        self.product.save()
        newest = Product.objects.create(name="New Rose", status="ACTIVE", category=self.category, supplier=self.supplier)
        response = self.client.get(reverse("users-home"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["new_arrivals"][0]["product"], newest)
        self.assertNotIn(newest, [card["product"] for card in response.context["products_with_images"]])

    def test_storefront_rejects_reversed_price_range(self):
        response = self.client.get(reverse("products:shop_homepage"), {"min_price": "100", "max_price": "10"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("max_price", response.context["form"].errors)

    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer",
            email="buyer@example.com",
            password="password123",
        )
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="password123",
        )
        Profile.objects.update_or_create(
            user=self.staff_user,
            defaults={"role": "staff", "bio": "Staff user"},
        )
        self.category = Category.objects.create(name="Fragrance")
        self.supplier = Supplier.objects.create(
            name="Primary Supplier",
            contact_name="Sam Supplier",
            email="primary@example.com",
            address="Kampala",
        )
        self.product = Product.objects.create(
            name="Citrus Roll-On",
            description="Fresh citrus scent.",
            status="ACTIVE",
            category=self.category,
            supplier=self.supplier,
        )
        self.volume = Volume.objects.create(
            ml=30,
            cost=Decimal("10.00"),
            price=Decimal("25.00"),
        )
        self.variant = ProductVolume.objects.create(
            product=self.product,
            volume=self.volume,
            product_type="Roll-On",
            stock_quantity=5,
            max_quantity_per_order=3,
        )

    def _cart_with_item(self, user=None, session_key=None, quantity=1):
        cart = Cart.objects.create(user=user, session_key=session_key)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            volume=self.variant,
            quantity=quantity,
        )
        return cart

    def test_cart_total_uses_variant_discounted_price(self):
        cart = Cart.objects.create(user=self.user)
        self.variant.discount_value = Decimal("20.00")
        self.variant.save()
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            volume=self.variant,
            quantity=2,
        )

        self.assertEqual(cart_total(cart), Decimal("40.00"))

    def test_wishlist_is_unique_per_user_and_product(self):
        Wishlist.objects.create(user=self.user, product=self.product)

        with self.assertRaises(IntegrityError):
            Wishlist.objects.create(user=self.user, product=self.product)

    def test_checkout_service_creates_order_details_and_clears_cart_without_reducing_stock(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            volume=self.variant,
            quantity=2,
        )

        order = create_order_from_cart(cart, payment_method="cod")

        self.assertEqual(order.customer.user, self.user)
        self.assertEqual(order.payment_method, "cod")
        self.assertEqual(order.details.count(), 1)
        self.assertEqual(order.details.first().total, Decimal("50.00"))
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 5)
        self.assertFalse(order.payments.exists())
        self.assertFalse(Sale.objects.filter(order=order).exists())
        self.assertFalse(cart.items.exists())

    def test_checkout_service_stores_guest_customer_and_mobile_money_number(self):
        cart = Cart.objects.create(session_key="guest-session")
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            volume=self.variant,
            quantity=1,
        )

        order = create_order_from_cart(
            cart,
            customer_data={
                "first_name": "Guest",
                "last_name": "Buyer",
                "email": "guest@example.com",
                "mobile": "+256772000000",
                "address": "Kampala Road",
            },
            payment_method="mobile",
            mobile_money_number="+256772000000",
            payment_evidence="TX12345",
        )

        self.assertIsNone(order.customer.user)
        self.assertEqual(order.customer.get_full_name(), "Guest Buyer")
        self.assertEqual(order.payment_method, "mobile")
        self.assertEqual(order.mobile_money_number, "+256772000000")
        self.assertEqual(order.transaction_id, "TX12345")
        self.assertFalse(cart.items.exists())

    def test_checkout_service_rejects_unavailable_stock(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            volume=self.variant,
            quantity=6,
        )

        with self.assertRaises(Exception):
            create_order_from_cart(cart, payment_method="cod")

        self.assertFalse(OrderDetail.objects.exists())
        self.assertTrue(cart.items.exists())

    def test_pay_on_delivery_payment_confirmation_records_payment_sale_and_stock_once(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            volume=self.variant,
            quantity=2,
        )
        order = create_order_from_cart(cart, payment_method="cod")

        self.assertEqual(order.payment_status, "pending")
        self.assertFalse(OrderPayment.objects.exists())
        self.assertFalse(Sale.objects.exists())
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 5)

        mark_order_paid_and_capture_sale(order, provider="cash", received_by=self.staff_user)
        mark_order_paid_and_capture_sale(order, provider="cash", received_by=self.staff_user)

        order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(order.payment_status, "completed")
        self.assertEqual(OrderPayment.objects.filter(order=order).count(), 1)
        self.assertEqual(Sale.objects.filter(order=order).count(), 1)
        self.assertEqual(SaleDetail.objects.filter(sale__order=order).count(), 1)
        self.assertEqual(self.variant.stock_quantity, 3)

    def test_flutterwave_success_is_idempotent(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            volume=self.variant,
            quantity=1,
        )
        order = create_order_from_cart(cart, payment_method="mobile")

        mark_order_paid_and_capture_sale(
            order,
            provider="flutterwave",
            transaction_id="flw-123",
            external_id="JBL-1",
        )
        mark_order_paid_and_capture_sale(
            order,
            provider="flutterwave",
            transaction_id="flw-123",
            external_id="JBL-1",
        )

        order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(order.payment_status, "completed")
        self.assertEqual(OrderPayment.objects.filter(order=order).count(), 1)
        self.assertEqual(Sale.objects.filter(order=order).count(), 1)
        self.assertEqual(self.variant.stock_quantity, 4)

    def test_empty_guest_checkout_returns_to_cart(self):
        response = self.client.get(reverse("orders:checkout"))
        self.assertRedirects(response, reverse("orders:cart"), fetch_redirect_response=False)

    def test_guest_with_items_can_checkout_without_login(self):
        session = self.client.session
        session.save()
        cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=cart, product=self.product, volume=self.variant, quantity=1)
        response = self.client.get(reverse("orders:checkout"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Complete your order")
        self.assertContains(response, 'id="checkoutForm"')

    def test_checkout_form_allows_pickup_without_delivery_address(self):
        station = PickupStation.objects.create(
            name="Main Pickup",
            city="Kampala",
            area="Central",
            address="Shop 1",
        )

        form = CheckoutForm(
            {
                "first_name": "Buyer",
                "last_name": "",
                "email": "buyer@example.com",
                "mobile": "+256777337491",
                "address": "",
                "delivery_region": "",
                "delivery_city": "",
                "delivery_area": "",
                "shipping_method": "pickup",
                "pickup_station": station.id,
                "payment_method": "cod",
            },
            user=self.user,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_checkout_form_normalizes_supported_ugandan_phone_formats(self):
        station = PickupStation.objects.create(
            name="Phone Test Pickup",
            city="Kampala",
            area="Central",
            address="Shop 2",
        )
        cases = {
            "+256701234567": "+256701234567",
            "+256751234567": "+256751234567",
            "0701234567": "+256701234567",
            "0751234567": "+256751234567",
            "0312345678": "+256312345678",
            "+256312345678": "+256312345678",
        }

        for supplied, expected in cases.items():
            with self.subTest(supplied=supplied):
                form = CheckoutForm(
                    {
                        "first_name": "Buyer",
                        "mobile": supplied,
                        "shipping_method": "pickup",
                        "pickup_station": station.id,
                        "payment_method": "cod",
                    },
                    user=self.user,
                )
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data["mobile"], expected)

    def test_checkout_form_shows_ugandan_phone_error_and_tel_keyboard_hint(self):
        form = CheckoutForm(
            {
                "first_name": "Buyer",
                "mobile": "+254701234567",
                "shipping_method": "pickup",
                "payment_method": "cod",
            },
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["mobile"][0],
            "Enter a valid Ugandan phone number. Example: +256701234567 or 0701234567",
        )
        self.assertEqual(form.fields["mobile"].widget.attrs["inputmode"], "tel")
        self.assertEqual(
            form.fields["mobile"].widget.attrs["placeholder"], "+256701234567"
        )

    def test_checkout_form_accepts_local_mobile_money_number(self):
        station = PickupStation.objects.create(
            name="Main Pickup",
            city="Kampala",
            area="Central",
            address="Shop 1",
        )

        form = CheckoutForm(
            {
                "first_name": "Buyer",
                "last_name": "",
                "email": "buyer@example.com",
                "mobile": "+256777337491",
                "address": "",
                "delivery_region": "",
                "delivery_city": "",
                "delivery_area": "",
                "shipping_method": "pickup",
                "pickup_station": station.id,
                "payment_method": "mobile",
                "mobile_money_number": "0772000000",
                "payment_evidence": "MM12345",
            },
            user=self.user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["mobile_money_number"], "0772000000")

    def test_checkout_form_rejects_international_mobile_money_number(self):
        station = PickupStation.objects.create(
            name="Main Pickup",
            city="Kampala",
            area="Central",
            address="Shop 1",
        )

        form = CheckoutForm(
            {
                "first_name": "Buyer",
                "last_name": "",
                "email": "buyer@example.com",
                "mobile": "+256777337491",
                "address": "",
                "delivery_region": "",
                "delivery_city": "",
                "delivery_area": "",
                "shipping_method": "pickup",
                "pickup_station": station.id,
                "payment_method": "mobile",
                "mobile_money_number": "+256772000000",
                "payment_evidence": "MM12345",
            },
            user=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors["mobile_money_number"]), 1)

    def test_guest_cart_merges_after_login(self):
        self.client.post(
            reverse("orders:add_to_cart", args=[self.product.uuid]),
            {"volume_id": self.variant.id, "quantity": "2"},
        )
        guest_session_key = self.client.session.session_key
        self.assertTrue(Cart.objects.filter(session_key=guest_session_key).exists())

        response = self.client.post(
            reverse("login"),
            {
                "username": "buyer",
                "password": "password123",
                "next": reverse("orders:checkout"),
            },
        )

        self.assertRedirects(response, reverse("orders:checkout"), fetch_redirect_response=False)
        user_cart = Cart.objects.get(user=self.user)
        self.assertEqual(user_cart.items.get(volume=self.variant).quantity, 2)
        self.assertFalse(Cart.objects.filter(session_key=guest_session_key).exists())

    def test_logged_in_customer_can_place_pay_on_delivery_order_without_payment_record(self):
        station = PickupStation.objects.create(
            name="Main Pickup",
            city="Kampala",
            area="Central",
            address="Shop 1",
        )
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            volume=self.variant,
            quantity=1,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "first_name": "Buyer",
                "last_name": "",
                "email": "buyer@example.com",
                "mobile": "+256777337491",
                "address": "",
                "delivery_region": "",
                "delivery_city": "",
                "delivery_area": "",
                "shipping_method": "pickup",
                "pickup_station": station.id,
                "payment_method": "cod",
            },
        )

        order = Order.objects.get(customer__user=self.user)
        self.assertRedirects(
            response,
            reverse("orders:order_confirmation", args=[order.id]),
            fetch_redirect_response=False,
        )
        self.assertEqual(order.payment_status, "pending")
        self.assertEqual(order.status, "Pending")
        self.assertFalse(order.payments.exists())
        self.assertFalse(Sale.objects.filter(order=order).exists())
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 5)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        RESEND_API_KEY="",
        ORDER_EMAIL_USE_CELERY=False,
        ADMIN_ORDER_EMAILS=["jobellinc@gmail.com"],
        JOBELL_ORDER_EMAIL="sales@jobellinc.com",
        DEFAULT_FROM_EMAIL="Jobell Inc <noreply@jobellinc.com>",
        RESEND_FROM_EMAIL="Jobell Inc <noreply@jobellinc.com>",
    )
    def test_order_creation_sends_customer_and_admin_emails(self):
        station = PickupStation.objects.create(
            name="Main Pickup",
            city="Kampala",
            area="Central",
            address="Shop 1",
        )
        self._cart_with_item(user=self.user)
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("orders:checkout"),
                {
                    "first_name": "Buyer",
                    "last_name": "",
                    "email": "buyer@example.com",
                    "mobile": "+256777337491",
                    "address": "",
                    "delivery_region": "",
                    "delivery_city": "",
                    "delivery_area": "",
                    "shipping_method": "pickup",
                    "pickup_station": station.id,
                    "payment_method": "cod",
                },
            )

        order = Order.objects.get(customer__user=self.user)
        self.assertRedirects(
            response,
            reverse("orders:order_confirmation", args=[order.id]),
            fetch_redirect_response=False,
        )
        self.assertEqual(len(mail.outbox), 2)
        recipients = {recipient for message in mail.outbox for recipient in message.to}
        self.assertEqual(recipients, {"buyer@example.com", "jobellinc@gmail.com", "sales@jobellinc.com"})
        self.assertTrue(any(f"order #{order.id}" in message.subject.lower() for message in mail.outbox))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        RESEND_API_KEY="",
        ORDER_EMAIL_USE_CELERY=False,
        ADMIN_ORDER_EMAILS=["jobellinc@gmail.com"],
        JOBELL_ORDER_EMAIL="sales@jobellinc.com",
    )
    def test_status_change_sends_customer_and_admin_emails(self):
        cart = self._cart_with_item(user=self.user)
        order = create_order_from_cart(cart, payment_method="cod")

        order.status = "Processing"
        order.save(update_fields=["status", "updated_at"])
        queue_order_status_changed_emails(order.id, "Pending", "Processing")

        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("Processing", mail.outbox[0].body)
        recipients = {recipient for message in mail.outbox for recipient in message.to}
        self.assertEqual(recipients, {"buyer@example.com", "jobellinc@gmail.com", "sales@jobellinc.com"})

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        RESEND_API_KEY="",
        ORDER_EMAIL_USE_CELERY=False,
        ADMIN_ORDER_EMAILS=["jobellinc@gmail.com"],
    )
    def test_payment_status_change_sends_customer_and_admin_emails(self):
        cart = self._cart_with_item(user=self.user)
        order = create_order_from_cart(cart, payment_method="mobile")
        old_status = order.payment_status
        mark_order_paid_and_capture_sale(order, provider="flutterwave", transaction_id="flw-email-1")
        order.refresh_from_db()

        queue_payment_status_changed_emails(order.id, old_status, order.payment_status)

        self.assertEqual(len(mail.outbox), 2)
        self.assertTrue(all("Payment completed" in message.subject for message in mail.outbox))

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        RESEND_API_KEY="",
        ORDER_EMAIL_USE_CELERY=False,
        ADMIN_ORDER_EMAILS=["jobellinc@gmail.com"],
    )
    def test_duplicate_order_save_does_not_send_duplicate_emails(self):
        cart = self._cart_with_item(user=self.user)
        order = create_order_from_cart(cart, payment_method="cod")
        order.save()

        self.assertEqual(mail.outbox, [])

    @override_settings(
        RESEND_API_KEY="",
        ORDER_EMAIL_USE_CELERY=False,
        ADMIN_ORDER_EMAILS=["jobellinc@gmail.com"],
    )
    @patch("apps.orders.notifications.send_transactional_email")
    def test_email_failure_does_not_rollback_order_creation(self, send_email):
        send_email.side_effect = EmailServiceError("boom")
        station = PickupStation.objects.create(
            name="Main Pickup",
            city="Kampala",
            area="Central",
            address="Shop 1",
        )
        self._cart_with_item(user=self.user)
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("orders:checkout"),
                {
                    "first_name": "Buyer",
                    "last_name": "",
                    "email": "buyer@example.com",
                    "mobile": "+256777337491",
                    "address": "",
                    "delivery_region": "",
                    "delivery_city": "",
                    "delivery_area": "",
                    "shipping_method": "pickup",
                    "pickup_station": station.id,
                    "payment_method": "cod",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Order.objects.filter(customer__user=self.user).exists())

    @override_settings(
        SITE_URL="https://jobellinc.com",
        LOGO_URL="/static/images/no-image.png",
        SUPPORT_EMAIL="support@jobellinc.com",
        SUPPORT_PHONE="+256 777 337491",
    )
    def test_all_order_email_templates_render_with_premium_context(self):
        cart = self._cart_with_item(user=self.user)
        order = create_order_from_cart(cart, payment_method="cod")
        order.status = "Delivered"
        order.total_amount = Decimal("1250000.00")
        order.shipping_fee = Decimal("25000.00")
        order.save(update_fields=["status", "total_amount", "shipping_fee", "updated_at"])

        contexts = [
            _order_context(order, "Order received", "Thank you for your order.", None, "Pending"),
            _order_context(order, "Payment completed", "Payment has been received.", "pending", "completed"),
            _order_context(order, "Order processing", "Your order is being prepared.", "Pending", "Processing"),
            _order_context(order, "Order shipped", "Your order has been shipped.", "Processing", "Shipped"),
            _order_context(order, "Out for delivery", "Your order is out for delivery.", "Shipped", "Out for Delivery"),
            _order_context(order, "Delivered", "Your order has been delivered.", "Out for Delivery", "Delivered"),
            _order_context(order, "Cancelled", "Your order has been cancelled.", "Pending", "Canceled"),
        ]
        templates = [
            "admin_new_order",
            "admin_order_notification",
            "order_confirmation",
            "order_notification",
            "order_status_update",
            "payment_confirmation",
        ]

        for context in contexts:
            for template_name in templates:
                html = render_to_string(f"emails/orders/{template_name}.html", context)
                text = render_to_string(f"emails/orders/{template_name}.txt", context)
                self.assertIn("UGX 1,250,000", html)
                self.assertIn("UGX 1,250,000", text)
                self.assertIn("https://jobellinc.com", html)
                self.assertIn("Order", text)

    def test_logged_in_customer_can_place_manual_mobile_money_order_with_evidence(self):
        station = PickupStation.objects.create(
            name="Main Pickup",
            city="Kampala",
            area="Central",
            address="Shop 1",
        )
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            volume=self.variant,
            quantity=1,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "first_name": "Buyer",
                "last_name": "",
                "email": "buyer@example.com",
                "mobile": "+256777337491",
                "address": "Plot 1",
                "delivery_region": CustomerAddress.Region.KAMPALA_AREA,
                "delivery_city": "Kampala",
                "delivery_area": "Central",
                "shipping_method": "pickup",
                "pickup_station": station.id,
                "payment_method": "mobile",
                "mobile_money_number": "0772000000",
                "payment_evidence": "MM12345",
            },
        )

        order = Order.objects.get(customer__user=self.user)
        self.assertRedirects(
            response,
            reverse("orders:order_confirmation", args=[order.id]),
            fetch_redirect_response=False,
        )
        self.assertEqual(order.payment_method, "mobile")
        self.assertEqual(order.payment_status, "pending")
        self.assertEqual(order.mobile_money_number, "0772000000")
        self.assertEqual(order.transaction_id, "MM12345")
        self.assertFalse(order.payments.exists())

    @patch("apps.orders.views._verify_flutterwave_transaction")
    def test_flutterwave_callback_marks_paid_and_captures_once(self, verify_transaction):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            volume=self.variant,
            quantity=1,
        )
        order = create_order_from_cart(cart, payment_method="mobile")
        self.client.force_login(self.user)
        Order.objects.filter(pk=order.pk).update(transaction_id="JBL-test-ref")
        order.refresh_from_db()
        session = self.client.session
        session["placed_order_ids"] = [order.id]
        session.save()
        verify_transaction.return_value = {
            "data": {
                "status": "successful",
                "tx_ref": "JBL-test-ref",
                "amount": "25.00",
                "currency": "UGX",
                "id": 999,
            }
        }

        url = reverse("orders:flutterwave_callback")
        for _ in range(2):
            response = self.client.get(
                url,
                {"tx_ref": "JBL-test-ref", "transaction_id": "999"},
            )
            self.assertRedirects(
                response,
                reverse("orders:order_confirmation", args=[order.id]),
                fetch_redirect_response=False,
            )

        order.refresh_from_db()
        self.variant.refresh_from_db()
        self.assertEqual(order.payment_status, "completed")
        self.assertEqual(order.payments.count(), 1)
        self.assertEqual(Sale.objects.filter(order=order).count(), 1)
        self.assertEqual(self.variant.stock_quantity, 4)

    def test_delivery_quote_uses_area_city_then_region_rates(self):
        DeliveryRate.objects.create(
            region=CustomerAddress.Region.KAMPALA_AREA,
            city="Kampala",
            area="Central",
            fee=Decimal("5000.00"),
        )
        DeliveryRate.objects.create(
            region=CustomerAddress.Region.KAMPALA_AREA,
            city="Kampala",
            area="",
            fee=Decimal("7000.00"),
        )
        DeliveryRate.objects.create(
            region=CustomerAddress.Region.KAMPALA_AREA,
            city="",
            area="",
            fee=Decimal("9000.00"),
        )

        area_quote = delivery_quote_for(
            CustomerAddress.Region.KAMPALA_AREA, "Kampala", "Central"
        )
        city_quote = delivery_quote_for(
            CustomerAddress.Region.KAMPALA_AREA, "Kampala", "Nakawa"
        )
        region_quote = delivery_quote_for(
            CustomerAddress.Region.KAMPALA_AREA, "Mukono", "Seeta"
        )

        self.assertTrue(area_quote.available)
        self.assertEqual(area_quote.fee, Decimal("5000.00"))
        self.assertEqual(area_quote.match_level, "area")
        self.assertEqual(city_quote.fee, Decimal("7000.00"))
        self.assertEqual(city_quote.match_level, "city")
        self.assertEqual(region_quote.fee, Decimal("9000.00"))
        self.assertEqual(region_quote.match_level, "region")

    def test_checkout_rejects_door_delivery_without_configured_rate(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(
            cart=cart,
            product=self.product,
            volume=self.variant,
            quantity=1,
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "first_name": "Buyer",
                "last_name": "",
                "email": "buyer@example.com",
                "mobile": "+256777337491",
                "address": "Plot 1 Unknown Road",
                "delivery_region": CustomerAddress.Region.WESTERN_REGION,
                "delivery_city": "Unknown City",
                "delivery_area": "Unknown Area",
                "shipping_method": "delivery",
                "payment_method": "cod",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Door delivery is not configured")
        self.assertFalse(Order.objects.filter(customer__user=self.user).exists())
        self.assertTrue(cart.items.exists())

    def test_order_report_requires_staff_role(self):
        customer = Customer.objects.create(
            user=self.user,
            first_name="Buyer",
            email="buyer@example.com",
        )
        order = Order.objects.create(customer=customer, total_amount=Decimal("25.00"))
        url = reverse("orders:order_report", args=[order.id])

        self.client.login(username="buyer", password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.login(username="staff", password="password123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
