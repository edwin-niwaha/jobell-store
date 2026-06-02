from decimal import Decimal

from django.test import TestCase

from apps.inventory.models import Inventory
from apps.inventory.services import backfill_default_product_variations
from apps.products.models import Category, Product, ProductVolume, Volume
from apps.supplier.models import Supplier


class InventoryVariationBackfillTests(TestCase):
    def test_backfill_creates_default_variation_from_legacy_product_stock(self):
        category = Category.objects.create(name="Perfume")
        supplier = Supplier.objects.create(
            name="Supplier",
            contact_name="Jane",
            email="supplier@example.com",
            address="Kampala",
        )
        Volume.objects.create(ml=100, cost=Decimal("100.00"), price=Decimal("200.00"))
        product = Product.objects.create(
            name="Queen of Victoria",
            description="Signature scent.",
            status="ACTIVE",
            category=category,
            supplier=supplier,
            selling_price=Decimal("200.00"),
            cost_price=Decimal("100.00"),
        )
        Inventory.objects.create(product=product, quantity=20)

        result = backfill_default_product_variations(Product.objects.filter(pk=product.pk))
        variant = ProductVolume.objects.get(product=product)

        self.assertEqual(result["created"], 1)
        self.assertEqual(variant.current_price, Decimal("200.00"))
        self.assertEqual(variant.available_quantity, 20)
        self.assertTrue(variant.is_in_stock)

    def test_single_default_variation_follows_legacy_inventory_update(self):
        category = Category.objects.create(name="Perfume")
        supplier = Supplier.objects.create(
            name="Supplier",
            contact_name="Jane",
            email="supplier@example.com",
            address="Kampala",
        )
        volume = Volume.objects.create(
            ml=100, cost=Decimal("100.00"), price=Decimal("200.00")
        )
        product = Product.objects.create(
            name="Victoria Mist",
            description="Signature scent.",
            status="ACTIVE",
            category=category,
            supplier=supplier,
            selling_price=Decimal("200.00"),
        )
        Inventory.objects.create(product=product, quantity=20)
        variant = ProductVolume.objects.create(
            product=product,
            volume=volume,
            product_type="Spray",
            price=Decimal("200.00"),
            stock_quantity=20,
        )

        inventory = product.inventory
        inventory.quantity = 7
        inventory.save()

        variant.refresh_from_db()
        self.assertEqual(variant.stock_quantity, 7)
