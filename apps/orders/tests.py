from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import Profile
from apps.addresses.models import CustomerAddress
from apps.customers.models import Customer
from apps.orders.models import Cart, CartItem, Order, OrderDetail, Wishlist
from apps.orders.services import cart_total, create_order_from_cart
from apps.products.models import Category, Product, ProductVolume, Volume
from apps.shipping.models import DeliveryRate
from apps.shipping.services import delivery_quote_for
from apps.supplier.models import Supplier


class EcommerceFlowTests(TestCase):
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

    def test_checkout_service_creates_order_details_and_clears_cart(self):
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
        self.assertEqual(self.variant.stock_quantity, 3)
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
        )

        self.assertIsNone(order.customer.user)
        self.assertEqual(order.customer.get_full_name(), "Guest Buyer")
        self.assertEqual(order.payment_method, "mobile")
        self.assertEqual(order.mobile_money_number, "+256772000000")
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
