from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from apps.inventory.models import Inventory
from apps.products.forms import ProductVolumeForm, VolumeForm
from apps.products.models import Category, Product, ProductVolume, Volume
from apps.products.selectors import build_storefront_product_card
from apps.supplier.models import Supplier


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Perfume")
        self.supplier = Supplier.objects.create(
            name="Example Supplier",
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

    def _product(self, name="Test Fragrance", **overrides):
        defaults = {
            "name": name,
            "description": "A production-safe scent.",
            "status": "ACTIVE",
            "category": self.category,
            "supplier": self.supplier,
        }
        defaults.update(overrides)
        return Product.objects.create(**defaults)

    def _variant(self, product, **overrides):
        defaults = {
            "product": product,
            "volume": self.volume,
            "product_type": "Spray",
            "price": Decimal("60.00"),
            "unit_cost": Decimal("25.00"),
        }
        defaults.update(overrides)
        return ProductVolume.objects.create(**defaults)

    def test_variant_available_quantity_uses_inventory_when_stock_untracked(self):
        product = self._product("Inventory Backed")
        Inventory.objects.create(product=product, quantity=6)
        variant = self._variant(product, stock_quantity=None)

        self.assertEqual(variant.available_quantity, 6)
        self.assertTrue(variant.is_stock_tracked)
        self.assertTrue(variant.is_in_stock)

    def test_variant_without_inventory_returns_zero_stock(self):
        product = self._product("Missing Inventory")
        variant = self._variant(product, stock_quantity=None)

        self.assertEqual(variant.available_quantity, 0)
        self.assertFalse(variant.is_stock_tracked)
        self.assertFalse(variant.is_in_stock)
        card = build_storefront_product_card(product)
        self.assertFalse(card["is_in_stock"])
        self.assertEqual(card["image_url"], "")

    def test_inactive_variant_is_not_in_stock(self):
        product = self._product("Inactive Variant")
        variant = self._variant(product, stock_quantity=5, is_active=False)

        self.assertEqual(variant.available_quantity, 5)
        self.assertFalse(variant.is_in_stock)
        card = build_storefront_product_card(product)
        self.assertFalse(card["is_in_stock"])
        self.assertEqual(card["variants"], [])

    def test_variant_with_zero_stock_is_not_sellable(self):
        product = self._product("Zero Stock")
        variant = self._variant(product, stock_quantity=0)

        self.assertEqual(variant.available_quantity, 0)
        self.assertFalse(variant.is_in_stock)
        card = build_storefront_product_card(product)
        self.assertFalse(card["is_in_stock"])
        self.assertEqual(card["sellable_variants"], [])

    def test_storefront_card_handles_variant_without_override_price(self):
        product = self._product("Volume Price Fallback")
        self._variant(product, price=None, stock_quantity=3)

        card = build_storefront_product_card(product)

        self.assertTrue(card["has_sellable_price"])
        self.assertEqual(card["min_price"], Decimal("35.00"))
        self.assertEqual(card["max_price"], Decimal("35.00"))

    def test_storefront_card_handles_product_with_inventory_and_no_active_variant(self):
        product = self._product("No Active Variant")
        Inventory.objects.create(product=product, quantity=4)

        card = build_storefront_product_card(product)

        self.assertTrue(card["is_in_stock"])
        self.assertEqual(card["variants"], [])
        self.assertFalse(card["has_sellable_price"])

    def test_volume_form_rejects_duplicate_ml(self):
        form = VolumeForm(
            data={
                "ml": "50",
                "cost": "10.00",
                "price": "20.00",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("already exists", form.errors["ml"][0])

    def test_product_volume_form_requires_variant_specific_prices(self):
        product = Product.objects.create(
            name="9PM",
            description="Evening scent.",
            status="ACTIVE",
            category=self.category,
            supplier=self.supplier,
        )

        form = ProductVolumeForm(
            data={
                "volume": self.volume.id,
                "product_type": "Mini",
                "stock_quantity": "5",
            },
            product=product,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("price", form.errors)
        self.assertIn("unit_cost", form.errors)

    def test_product_volume_form_rejects_duplicate_product_variant(self):
        product = Product.objects.create(
            name="Khamrah",
            description="Spiced scent.",
            status="ACTIVE",
            category=self.category,
            supplier=self.supplier,
        )
        ProductVolume.objects.create(
            product=product,
            volume=self.volume,
            product_type="Mini",
            price=Decimal("25000.00"),
            unit_cost=Decimal("15000.00"),
        )

        form = ProductVolumeForm(
            data={
                "volume": self.volume.id,
                "product_type": "Mini",
                "price": "30000.00",
                "unit_cost": "18000.00",
            },
            product=product,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("already has Mini - 50ML", form.non_field_errors()[0])
