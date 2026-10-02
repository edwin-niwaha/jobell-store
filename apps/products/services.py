from decimal import Decimal

from django.utils.text import slugify


def generate_unique_slug(model_class, value, instance=None, field_name="slug"):
    """Generate a stable, readable slug without requiring callers to know model internals."""
    base_slug = slugify(value or "") or "item"
    slug = base_slug
    counter = 2

    queryset = model_class.objects.filter(**{field_name: slug})
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
        queryset = model_class.objects.filter(**{field_name: slug})
        if instance and instance.pk:
            queryset = queryset.exclude(pk=instance.pk)

    return slug


def normalize_sku(value):
    return (value or "").strip().upper().replace(" ", "-")


def generate_variant_sku(product, variant_name, instance=None):
    product_code = slugify(getattr(product, "name", "") or "product").upper()
    variant_code = slugify(variant_name or "variant").upper()
    base_sku = normalize_sku(f"JBL-{product_code[:16]}-{variant_code[:16]}")
    sku = base_sku
    counter = 2

    from .models import ProductVolume

    queryset = ProductVolume.objects.filter(sku=sku)
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.exists():
        sku = f"{base_sku}-{counter}"
        counter += 1
        queryset = ProductVolume.objects.filter(sku=sku)
        if instance and instance.pk:
            queryset = queryset.exclude(pk=instance.pk)

    return sku


def percentage_discount(price, discount_value):
    price = Decimal(price or 0)
    discount_value = Decimal(discount_value or 0)
    if discount_value <= 0:
        return price
    discounted = price - (price * discount_value / Decimal("100"))
    return max(Decimal("0"), discounted)
