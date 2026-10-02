from django.db.models import Q

from apps.products.models import Category, Product, ProductVolume
from apps.products.selectors import active_products_queryset, active_variants_queryset


class ProductRepository:
    """Read-side product access for web and API layers."""

    def list_categories(self):
        return Category.objects.filter(is_active=True).order_by("name")

    def list_products(self, *, search="", category=None, featured=None, active=True):
        queryset = active_products_queryset() if active else Product.objects.all()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(category__name__icontains=search)
                | Q(productvolume__sku__icontains=search)
                | Q(productvolume__name__icontains=search)
            ).distinct()
        if category:
            category_filter = Q(category__slug=category)
            if str(category).isdigit():
                category_filter |= Q(category_id=category)
            queryset = queryset.filter(category_filter)
        if featured is not None:
            queryset = queryset.filter(is_featured=featured)

        return queryset.order_by("name")

    def get_product(self, lookup):
        query = Q(slug=lookup) | Q(uuid=lookup)
        if str(lookup).isdigit():
            query |= Q(pk=lookup)
        return active_products_queryset().filter(query).first()

    def list_product_variants(self, product):
        return active_variants_queryset().filter(product=product)


class ProductVariantRepository:
    def get_active_variant(self, variant_id):
        return (
            ProductVolume.objects.select_related("product", "volume")
            .filter(pk=variant_id, is_active=True, product__status="ACTIVE")
            .first()
        )
