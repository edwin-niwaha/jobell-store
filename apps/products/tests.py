from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from apps.products.models import Category, Product, ProductVolume, Volume
from apps.products.selectors import build_storefront_product_card
from apps.supplier.models import Supplier


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Perfume")
        self.supplier = Supplier.objects.create(
            name="Jobell Supplier",
            contact_name="Jane Supplier",
            email="supplier@example.com",
            address="Kampala",
        )
        self.volume = Volume.objects.create(
            ml=50,
            cost=Decimal("20.00"),
            price=Decimal("35.00"),
        )

    def test_product_creation_generates_unique_slug(self):
        first = Product.objects.create(
            name="Rose Mist",
            description="A floral fragrance.",
            status="ACTIVE",
            category=self.category,
            supplier=self.supplier,
        )
        second = Product.objects.create(
            name="Rose Mist",
            description="A second floral fragrance.",
            status="ACTIVE",
            category=self.category,
            supplier=self.supplier,
        )

        self.assertTrue(first.slug.startswith("rose-mist"))
        self.assertTrue(second.slug.startswith("rose-mist"))
        self.assertNotEqual(first.slug, second.slug)

    def test_product_variant_enforces_unique_combination_and_sku(self):
        product = Product.objects.create(
            name="Amber Spray",
            description="Warm amber scent.",
            status="ACTIVE",
            category=self.category,
            supplier=self.supplier,
        )
        ProductVolume.objects.create(
            product=product,
            volume=self.volume,
            product_type="Spray",
            sku="AMB-50",
        )

        with self.assertRaises(IntegrityError):
            ProductVolume.objects.create(
                product=product,
                volume=self.volume,
                product_type="Spray",
                sku="AMB-50-DUP",
            )

    def test_variant_current_price_uses_override_and_discount(self):
        product = Product.objects.create(
            name="Cedar Roll-On",
            description="Woody scent.",
            status="ACTIVE",
            category=self.category,
            supplier=self.supplier,
        )
        variant = ProductVolume.objects.create(
            product=product,
            volume=self.volume,
            product_type="Roll-On",
            price=Decimal("50.00"),
            discount_value=Decimal("10.00"),
        )

        self.assertEqual(variant.original_price, Decimal("50.00"))
        self.assertEqual(variant.current_price, Decimal("45.00"))
        self.assertTrue(variant.has_price_discount)

    def test_storefront_card_uses_sellable_variant_price_range(self):
        product = Product.objects.create(
            name="Citrus Spray",
            description="Bright citrus scent.",
            status="ACTIVE",
            category=self.category,
            supplier=self.supplier,
        )
        ProductVolume.objects.create(
            product=product,
            volume=self.volume,
            product_type="Spray",
            price=Decimal("60.00"),
            discount_value=Decimal("25.00"),
            stock_quantity=4,
        )

        card = build_storefront_product_card(product)

        self.assertTrue(card["has_sellable_price"])
        self.assertTrue(card["has_discount"])
        self.assertTrue(card["is_in_stock"])
        self.assertEqual(card["min_price"], Decimal("45.00"))
        self.assertEqual(card["max_price"], Decimal("45.00"))
        self.assertEqual(card["min_original_price"], Decimal("60.00"))
