from django.contrib import admin

from .models import Cart, CartItem, Order, OrderDetail, Wishlist


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ("product", "volume")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("user__username", "session_key")
    raw_id_fields = ("user",)
    inlines = (CartItemInline,)


class OrderDetailInline(admin.TabularInline):
    model = OrderDetail
    extra = 0
    raw_id_fields = ("product", "product_volume")
    readonly_fields = ("total",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "status",
        "payment_status",
        "payment_method",
        "shipping_method",
        "shipping_fee",
        "total_amount",
        "created_at",
    )
    list_filter = (
        "status",
        "payment_status",
        "payment_method",
        "shipping_method",
        "delivery_region",
        "created_at",
    )
    search_fields = (
        "id",
        "customer__first_name",
        "customer__last_name",
        "customer__email",
        "transaction_id",
        "external_id",
        "delivery_address_text",
    )
    raw_id_fields = ("customer", "pickup_station")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    inlines = (OrderDetailInline,)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "volume", "quantity", "updated_at")
    search_fields = ("product__name", "volume__sku", "cart__user__username")
    raw_id_fields = ("cart", "product", "volume")


@admin.register(OrderDetail)
class OrderDetailAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "product_volume", "quantity", "price", "discounted_price", "total")
    search_fields = ("order__id", "product__name", "product_volume__sku")
    raw_id_fields = ("order", "product", "product_volume")


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "added_at")
    list_filter = ("added_at",)
    search_fields = ("user__username", "product__name")
    raw_id_fields = ("user", "product")
