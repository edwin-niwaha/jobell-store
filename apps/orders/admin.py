from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Cart, CartItem, Order, OrderDetail, OrderPayment, Wishlist
from .notifications import (
    queue_order_status_changed_emails,
    queue_payment_status_changed_emails,
)
from .services import mark_order_paid_and_capture_sale


@admin.action(description="Confirm payment received and record sale")
def confirm_payment_received(modeladmin, request, queryset):
    confirmed = 0
    skipped = 0
    failed = 0
    for order in queryset.select_related("customer"):
        old_payment_status = order.payment_status
        try:
            payment, sale, sale_created = mark_order_paid_and_capture_sale(
                order,
                provider="cash" if order.payment_method == "cod" else "mobile_money",
                received_by=request.user,
            )
            order.refresh_from_db(fields=["payment_status"])
            if old_payment_status != order.payment_status:
                transaction.on_commit(
                    lambda order_id=order.id,
                    old_status=old_payment_status,
                    new_status=order.payment_status: queue_payment_status_changed_emails(
                        order_id,
                        old_status,
                        new_status,
                    )
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

    def get_readonly_fields(self, request, obj=None):
        return (
            *super().get_readonly_fields(request, obj),
            "email_notification_summary",
        )

    @admin.display(description="Email notifications")
    def email_notification_summary(self, obj):
        if obj is None:
            return "Notifications are sent after order creation and status/payment transitions."
        customer_email = obj.customer.email if obj.customer_id else ""
        return (
            f"Customer: {customer_email or 'missing'} | "
            f"Admin recipients: configured via JOBELL_ORDER_EMAIL/ADMIN_ORDER_EMAILS | "
            "Failures are written to logs/app.log"
        )

    def save_model(self, request, obj, form, change):
        old_status = None
        old_payment_status = None
        if change and obj.pk:
            previous = Order.objects.filter(pk=obj.pk).values("status", "payment_status").first()
            if previous:
                old_status = previous["status"]
                old_payment_status = previous["payment_status"]

        super().save_model(request, obj, form, change)

        if change and old_status is not None and old_status != obj.status:
            transaction.on_commit(
                lambda order_id=obj.id,
                old=old_status,
                new=obj.status: queue_order_status_changed_emails(order_id, old, new)
            )
        if (
            change
            and old_payment_status is not None
            and old_payment_status != obj.payment_status
        ):
            transaction.on_commit(
                lambda order_id=obj.id,
                old=old_payment_status,
                new=obj.payment_status: queue_payment_status_changed_emails(order_id, old, new)
            )


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
