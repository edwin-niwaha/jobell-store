"""Order/cart domain services.

Keep money, cart and checkout rules here so views stay thin and the same logic can be
reused by HTMX views, APIs, management commands and tests.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError

from apps.customers.models import Customer
from apps.inventory.models import Inventory
from apps.inventory.services import sync_product_inventory_from_variations
from apps.products.models import ProductVolume
from .models import Cart, CartItem, Order, OrderDetail


def get_or_create_cart(request):
    if request.user.is_authenticated:
        return Cart.objects.get_or_create(user=request.user, session_key=None)[0]
    if not request.session.session_key:
        request.session.create()
    return Cart.objects.get_or_create(session_key=request.session.session_key, user=None)[0]


def cart_total(cart):
    return sum(
        (item.get_total_price() for item in cart.items.select_related("volume", "volume__volume")),
        Decimal("0"),
    )


def _clean_customer_data(customer_data):
    data = customer_data or {}
    return {
        "first_name": data.get("first_name") or "Guest",
        "last_name": data.get("last_name") or "",
        "email": data.get("email") or "",
        "mobile": data.get("mobile") or None,
        "address": data.get("address") or "",
    }


def _validate_cart_items(cart):
    items = list(
        cart.items.select_related("product", "volume", "volume__volume").order_by("id")
    )
    if not items:
        raise ValueError("Cannot create an order from an empty cart.")

    for item in items:
        variant = item.volume
        if not variant.is_active or not item.product.is_active:
            raise ValidationError(
                f"{item.product.name} ({variant.variant_label}) is no longer available."
            )
        if item.quantity <= 0:
            raise ValidationError(f"{item.product.name} has an invalid quantity.")
        if (
            variant.max_quantity_per_order
            and item.quantity > variant.max_quantity_per_order
        ):
            raise ValidationError(
                f"You can order up to {variant.max_quantity_per_order} units of "
                f"{item.product.name} ({variant.variant_label})."
            )
        if item.quantity > variant.available_quantity:
            raise ValidationError(
                f"Only {variant.available_quantity} units of {item.product.name} "
                f"({variant.variant_label}) are available."
            )
    return items


@transaction.atomic
def create_order_from_cart(
    cart,
    customer_data=None,
    payment_method="cod",
    mobile_money_number="",
    shipping_data=None,
):
    items = _validate_cart_items(cart)
    if cart.user:
        customer, _ = Customer.objects.get_or_create(
            user=cart.user,
            defaults={
                "first_name": cart.user.first_name or cart.user.username,
                "last_name": cart.user.last_name,
                "email": cart.user.email,
            },
        )
        for field, value in _clean_customer_data(customer_data).items():
            if value not in (None, ""):
                setattr(customer, field, value)
        customer.save()
    else:
        customer = Customer.objects.create(**_clean_customer_data(customer_data))

    shipping_data = shipping_data or {}
    order = Order.objects.create(
        customer=customer,
        payment_method=payment_method,
        mobile_money_number=mobile_money_number if payment_method == "mobile" else "",
        status="Pending",
        payment_status="pending",
        total_amount=cart_total(cart) + shipping_data.get("shipping_fee", Decimal("0.00")),
        shipping_method=shipping_data.get("shipping_method", "delivery"),
        shipping_fee=shipping_data.get("shipping_fee", Decimal("0.00")),
        delivery_address_text=shipping_data.get("delivery_address_text", ""),
        delivery_region=shipping_data.get("delivery_region", ""),
        pickup_station=shipping_data.get("pickup_station"),
    )
    for item in items:
        OrderDetail.objects.create(
            order=order,
            product=item.product,
            product_volume=item.volume,
            quantity=item.quantity,
            price=item.volume.effective_price,
            discounted_price=item.volume.get_discounted_price(),
        )
        if item.volume.stock_quantity is not None:
            updated = ProductVolume.objects.filter(
                pk=item.volume_id,
                stock_quantity__gte=item.quantity,
            ).update(stock_quantity=F("stock_quantity") - item.quantity)
            if not updated:
                raise ValidationError(
                    f"{item.product.name} ({item.volume.variant_label}) sold out "
                    "before checkout completed. Please review your cart."
                )
            sync_product_inventory_from_variations(item.product)
        elif hasattr(item.product, "inventory"):
            updated = Inventory.objects.filter(
                product=item.product,
                quantity__gte=item.quantity,
            ).update(quantity=F("quantity") - item.quantity)
            if not updated:
                raise ValidationError(
                    f"{item.product.name} ({item.volume.variant_label}) sold out "
                    "before checkout completed. Please review your cart."
                )
    cart.items.all().delete()
    return order
