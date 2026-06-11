from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Cart, CartItem, Order, OrderDetail, OrderPayment, Wishlist
from .services import mark_order_paid_and_capture_sale


@admin.action(description="Confirm payment received and record sale")
def confirm_payment_received(modeladmin, request, queryset):
    confirmed = 0
    skipped = 0
    failed = 0
    for order in queryset.select_related("customer"):
        try:
            payment, sale, sale_created = mark_order_paid_and_capture_sale(
                order,
                provider="cash" if order.payment_method == "cod" else "mobile_money",
                received_by=request.user,
            )
            if sale_created:
                confirmed += 1
            else:
                skipped += 1
        except ValidationError as exc:
            failed += 1
            modeladmin.message_user(request, f"Order {order.id}: {exc}", level="ERROR")
    if confirmed:
        modeladmin.message_user(request, f"{confirmed} order payment(s) confirmed.")
    if skipped:
        modeladmin.message_user(request, f"{skipped} order(s) were already recorded.")
    if failed:
        modeladmin.message_user(request, f"{failed} order(s) could not be confirmed.", level="ERROR")


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
    actions = (confirm_payment_received,)


@admin.register(OrderPayment)
class OrderPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "provider", "amount", "currency", "transaction_id", "created_at")
    list_filter = ("provider", "currency", "created_at")
    search_fields = ("order__id", "transaction_id", "external_id")
    raw_id_fields = ("order", "received_by")
    readonly_fields = ("created_at",)


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
