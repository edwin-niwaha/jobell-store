from rest_framework import serializers

from apps.addresses.models import CustomerAddress
from apps.orders.models import Cart, CartItem, Order, OrderDetail, Wishlist
from .product_serializers import ProductSerializer, ProductVariantSerializer


class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = [
            "id",
            "street_name",
            "city",
            "area",
            "phone_number",
            "additional_telephone",
            "additional_information",
            "region",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    variant = ProductVariantSerializer(source="volume", read_only=True)
    unit_price = serializers.DecimalField(source="volume.current_price", max_digits=10, decimal_places=2, read_only=True)
    line_total = serializers.DecimalField(source="get_total_price", max_digits=12, decimal_places=2, read_only=True)
    variant_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = CartItem
        fields = ["id", "product", "variant", "variant_id", "quantity", "unit_price", "line_total"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total_items", "total_price"]

    def get_total_items(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_total_price(self, obj):
        return obj.get_total_price()


class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    variant_name = serializers.CharField(source="product_volume.variant_label", read_only=True)
    line_total = serializers.DecimalField(source="total", max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderDetail
        fields = [
            "id",
            "product",
            "product_volume",
            "product_title",
            "product_slug",
            "variant_name",
            "quantity",
            "price",
            "discounted_price",
            "line_total",
        ]


class OrderSerializer(serializers.ModelSerializer):
    slug = serializers.SerializerMethodField()
    items = OrderItemSerializer(source="details", many=True, read_only=True)
    total_price = serializers.DecimalField(source="total_amount", max_digits=12, decimal_places=2, read_only=True)
    pickup_station_name = serializers.CharField(source="pickup_station.name", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "slug",
            "status",
            "payment_method",
            "payment_status",
            "shipping_method",
            "shipping_fee",
            "tax_amount",
            "total_price",
            "delivery_address_text",
            "delivery_region",
            "pickup_station",
            "pickup_station_name",
            "items",
            "created_at",
            "updated_at",
        ]

    def get_slug(self, obj):
        return f"JBL-{obj.id}"


class CheckoutSerializer(serializers.Serializer):
    address_id = serializers.IntegerField()
    delivery_option = serializers.ChoiceField(
        choices=["HOME_DELIVERY", "PICKUP_STATION"],
        default="HOME_DELIVERY",
        required=False,
    )
    pickup_station_id = serializers.IntegerField(required=False, allow_null=True)
    payment_method = serializers.CharField(default="cod", required=False)
    description = serializers.CharField(required=False, allow_blank=True)


class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "product", "added_at"]
