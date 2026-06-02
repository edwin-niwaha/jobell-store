"""Read-optimized product querysets and storefront presentation helpers."""

from django.db.models import Prefetch
from django.db.models import Avg, Q

from .models import Product, ProductImage, ProductVolume


def active_variants_queryset():
    return (
        ProductVolume.objects.filter(is_active=True)
        .select_related("volume", "product", "product__category")
        .order_by("sort_order", "volume__ml", "product_type", "color", "size", "scent")
    )


def sellable_variants_queryset():
    return active_variants_queryset().filter(
        Q(stock_quantity__isnull=True) | Q(stock_quantity__gt=0)
    )


def active_products_queryset():
    active_variants = active_variants_queryset()
    active_images = ProductImage.objects.filter(is_active=True)
    return (
        Product.objects.select_related("category", "supplier", "inventory")
        .prefetch_related(
            Prefetch("productvolume_set", queryset=active_variants, to_attr="prefetched_active_variants"),
            Prefetch("images", queryset=active_images, to_attr="prefetched_active_images"),
        )
        .filter(status="ACTIVE")
    )


def _variant_current_price(variant):
    return variant.current_price


def build_storefront_product_card(product):
    images = getattr(product, "prefetched_active_images", None)
    if images is None:
        images = list(product.images.filter(is_active=True).order_by("sort_order", "-created_at"))

    default_image = next((image for image in images if image.is_default), None)
    first_image = default_image or (images[0] if images else None)
    image_url = product.hero_image_url or (first_image.image_url if first_image else "")

    variants = getattr(product, "prefetched_active_variants", None)
    if variants is None:
        variants = list(active_variants_queryset().filter(product=product))

    sellable_variants = [
        variant
        for variant in variants
        if variant.is_in_stock and _variant_current_price(variant) is not None
    ]
    priced_variants = sellable_variants or [
        variant for variant in variants if _variant_current_price(variant) is not None
    ]

    prices = [_variant_current_price(variant) for variant in priced_variants]
    original_prices = [
        variant.original_price
        for variant in priced_variants
        if variant.original_price is not None
    ]

    min_price = min(prices) if prices else product.selling_price
    max_price = max(prices) if prices else product.selling_price
    min_original_price = min(original_prices) if original_prices else product.selling_price
    has_discount = any(variant.has_price_discount for variant in priced_variants)
    has_sellable_price = min_price is not None and max_price is not None

    if not image_url:
        image_url = next((variant.image_url for variant in variants if variant.image_url), "")

    avg_rating = product.reviews.filter(is_verified=True).aggregate(Avg("rating"))[
        "rating__avg"
    ]

    fallback_stock = getattr(getattr(product, "inventory", None), "quantity", 0)
    is_in_stock = bool(sellable_variants) or (not variants and fallback_stock > 0)
    volume_values = sorted(
        {
            variant.volume.ml
            for variant in (sellable_variants or priced_variants or variants)
            if variant.volume_id and variant.volume and variant.volume.ml is not None
        }
    )
    if len(volume_values) > 1:
        volume_range_label = f"{volume_values[0]}ML - {volume_values[-1]}ML"
    elif volume_values:
        volume_range_label = f"{volume_values[0]}ML"
    else:
        volume_range_label = ""

    return {
        "product": product,
        "images": images,
        "image_url": image_url,
        "min_price": min_price,
        "max_price": max_price,
        "min_original_price": min_original_price,
        "has_discount": has_discount,
        "has_sellable_price": has_sellable_price,
        "is_in_stock": is_in_stock,
        "avg_rating": round(avg_rating, 1) if avg_rating else None,
        "variants": variants,
        "sellable_variants": sellable_variants,
        "volume_range_label": volume_range_label,
    }


def build_storefront_cards(products):
    return [build_storefront_product_card(product) for product in products]
