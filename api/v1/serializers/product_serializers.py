from rest_framework import serializers

from apps.products.models import Category, Product, ProductImage, ProductVolume


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "image_url", "is_active"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image_url", "alt_text", "is_default", "is_active", "sort_order"]


class ProductVariantSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(source="current_price", max_digits=10, decimal_places=2, read_only=True)
    original_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    stock_quantity = serializers.IntegerField(source="available_quantity", read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    image_url = serializers.CharField(read_only=True)
    volume_ml = serializers.IntegerField(source="volume.ml", read_only=True)

    class Meta:
        model = ProductVolume
        fields = [
            "id",
            "name",
            "variant_label",
            "sku",
            "price",
            "original_price",
            "stock_quantity",
            "max_quantity_per_order",
            "is_active",
            "is_in_stock",
            "sort_order",
            "image_url",
            "volume_ml",
        ]


class ProductSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True)
    category = CategorySerializer(read_only=True)
    variants = ProductVariantSerializer(source="active_variants", many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    primary_image = serializers.SerializerMethodField()
    image_urls = serializers.ListField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "uuid",
            "title",
            "name",
            "slug",
            "description",
            "hero_image_url",
            "primary_image",
            "image_urls",
            "is_active",
            "is_featured",
            "base_price",
            "is_in_stock",
            "category",
            "variants",
            "images",
            "average_rating",
            "total_reviews",
            "created_at",
        ]

    def get_primary_image(self, obj):
        image = obj.primary_image
        return image.image_url if image else obj.hero_image_url
