"""Inventory domain helpers."""

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F, Q

from apps.products.models import Product, ProductVolume, Volume
from .models import Inventory


def _product_inventory_quantity(product, default=0):
    try:
        return product.inventory.quantity or default
    except ObjectDoesNotExist:
        return default


def product_variation_stock(product):
    variants = product.productvolume_set.filter(is_active=True)
    tracked = variants.filter(stock_quantity__isnull=False)
    if tracked.exists():
        return sum(variant.stock_quantity or 0 for variant in tracked)
    return _product_inventory_quantity(product)


def sync_product_inventory_from_variations(product):
    quantity = product_variation_stock(product)
    inventory, _ = Inventory.objects.get_or_create(product=product)
    if inventory.quantity != quantity:
        inventory.quantity = quantity
        inventory.save(update_fields=["quantity", "is_out_of_stock", "updated_at"])
    return inventory


def ensure_default_product_variation(product, volume=None):
    if product.productvolume_set.exists():
        return None
    volume = volume or Volume.objects.order_by("ml").first()
    if volume is None:
        return None
    inventory_quantity = _product_inventory_quantity(product, default=None)
    return ProductVolume.objects.create(
        product=product,
        volume=volume,
        product_type="Spray",
        price=product.selling_price if product.selling_price is not None else None,
        unit_cost=product.cost_price if product.cost_price is not None else None,
        stock_quantity=inventory_quantity,
        max_quantity_per_order=10,
        is_active=True,
    )


def backfill_default_product_variations(queryset=None):
    products = queryset or Product.objects.filter(status="ACTIVE")
    created = 0
    skipped = 0
    volume = Volume.objects.order_by("ml").first()
    for product in products.select_related("inventory"):
        variant = ensure_default_product_variation(product, volume=volume)
        if variant is None:
            skipped += 1
        else:
            created += 1
    return {"created": created, "skipped": skipped}


def low_stock_queryset():
    return Inventory.objects.select_related("product", "product__category").filter(
        quantity__gt=0,
        quantity__lte=F("low_stock_threshold"),
    )


def out_of_stock_queryset():
    return Inventory.objects.select_related("product", "product__category").filter(
        Q(quantity=0) | Q(is_out_of_stock=True)
    )
