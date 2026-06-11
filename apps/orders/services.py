"""Order/cart domain services.

Keep money, cart and checkout rules here so views stay thin and the same logic can be
reused by HTMX views, APIs, management commands and tests.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.customers.models import Customer
from apps.inventory.models import Inventory
from apps.inventory.services import sync_product_inventory_from_variations
from apps.products.models import ProductVolume
from apps.sales.models import Sale, SaleDetail
from .models import Cart, CartItem, Order, OrderDetail, OrderPayment


def get_or_create_cart(request):
    if request.user.is_authenticated:
        return Cart.objects.get_or_create(user=request.user, session_key=None)[0]
    if not request.session.session_key:
        request.session.create()
    return Cart.objects.get_or_create(session_key=request.session.session_key, user=None)[0]


@transaction.atomic
def merge_session_cart_into_user_cart(session_key, user):
    if not session_key or not user or not user.is_authenticated:
        return Cart.objects.get_or_create(user=user, session_key=None)[0] if user else None

    user_cart, _ = Cart.objects.get_or_create(user=user, session_key=None)
    guest_cart = (
        Cart.objects.select_for_update()
        .prefetch_related("items")
        .filter(session_key=session_key, user__isnull=True)
        .first()
    )
    if not guest_cart or guest_cart.pk == user_cart.pk:
        return user_cart

    for guest_item in guest_cart.items.select_for_update().select_related("volume", "product"):
        cart_item, _ = CartItem.objects.select_for_update().get_or_create(
            cart=user_cart,
            volume=guest_item.volume,
            defaults={
                "product": guest_item.product,
                "quantity": 0,
            },
        )
        max_quantity = guest_item.volume.max_quantity_per_order or guest_item.volume.available_quantity
        available_quantity = guest_item.volume.available_quantity
        cart_item.product = guest_item.product
        cart_item.quantity = min(
            cart_item.quantity + guest_item.quantity,
            max_quantity,
            available_quantity,
        )
        if cart_item.quantity > 0:
            cart_item.save()
    guest_cart.delete()
    return user_cart


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
    payment_evidence="",
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
        transaction_id=payment_evidence if payment_method == "mobile" else "",
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
    cart.items.all().delete()
    return order


def _payment_provider_for_order(order):
    if order.payment_method == "mobile":
        return "flutterwave"
    if order.payment_method == "cod":
        return "cash"
    return "other"


def _sale_payment_method_for_order(order):
    if order.payment_method == "mobile":
        return "mobile_money"
    if order.payment_method == "cod":
        return "cash"
    return "other"


def _reduce_stock_for_detail(detail):
    variant = detail.product_volume
    if variant.stock_quantity is not None:
        updated = ProductVolume.objects.filter(
            pk=variant.pk,
            stock_quantity__gte=detail.quantity,
        ).update(stock_quantity=F("stock_quantity") - detail.quantity)
        if not updated:
            raise ValidationError(
                f"Not enough stock for {detail.product.name} ({variant.variant_label})."
            )
        variant.refresh_from_db(fields=["stock_quantity"])
        sync_product_inventory_from_variations(detail.product)
        return

    updated = Inventory.objects.filter(
        product=detail.product,
        quantity__gte=detail.quantity,
    ).update(quantity=F("quantity") - detail.quantity)
    if not updated:
        raise ValidationError(
            f"Not enough stock for {detail.product.name} ({variant.variant_label})."
        )


def _capture_sale_locked(order):
    existing_sale = Sale.objects.select_for_update().filter(order=order).first()
    if existing_sale:
        return existing_sale, False

    details = list(
        order.details.select_related("product", "product_volume", "product_volume__volume")
        .select_for_update()
        .order_by("id")
    )
    if not details:
        raise ValidationError("This order has no items to record.")

    subtotal = sum((detail.total for detail in details), Decimal("0.00"))
    sale = Sale.objects.create(
        order=order,
        sale_type="online",
        trans_date=timezone.localdate(),
        receipt_number=f"ORDER-{order.id}",
        customer=order.customer,
        sub_total=float(subtotal),
        grand_total=float(order.total_amount),
        tax_amount=float(order.tax_amount),
        tax_percentage=float(order.tax_percentage),
        amount_payed=float(order.total_amount),
        amount_change=0,
        payment_method=_sale_payment_method_for_order(order),
    )

    for detail in details:
        _reduce_stock_for_detail(detail)
        unit_price = detail.discounted_price if detail.discounted_price is not None else detail.price
        SaleDetail.objects.create(
            sale=sale,
            product=detail.product,
            product_volume=detail.product_volume,
            price=float(unit_price),
            quantity=detail.quantity,
            total_detail=float(detail.total),
        )
    return sale, True


@transaction.atomic
def capture_order_sale(order):
    locked_order = (
        Order.objects.select_for_update()
        .select_related("customer")
        .prefetch_related("details")
        .get(pk=order.pk)
    )
    return _capture_sale_locked(locked_order)


@transaction.atomic
def mark_order_paid_and_capture_sale(
    order,
    *,
    provider=None,
    amount=None,
    currency="UGX",
    transaction_id="",
    external_id="",
    received_by=None,
):
    locked_order = Order.objects.select_for_update().select_related("customer").get(pk=order.pk)
    provider = provider or _payment_provider_for_order(locked_order)
    amount = amount if amount is not None else locked_order.total_amount
    transaction_id = transaction_id or ""
    external_id = external_id or ""

    payment = None
    if transaction_id:
        payment = OrderPayment.objects.select_for_update().filter(
            provider=provider,
            transaction_id=transaction_id,
        ).first()
    if payment is None:
        payment = OrderPayment.objects.select_for_update().filter(
            order=locked_order,
            provider=provider,
        ).first()
    if payment is None:
        payment = OrderPayment.objects.create(
            order=locked_order,
            provider=provider,
            amount=amount,
            currency=currency,
            transaction_id=transaction_id,
            external_id=external_id,
            received_by=received_by,
        )

    sale, sale_created = _capture_sale_locked(locked_order)

    changed_fields = []
    if locked_order.payment_status != "completed":
        locked_order.payment_status = "completed"
        changed_fields.append("payment_status")
    if locked_order.amount_paid != locked_order.total_amount:
        locked_order.amount_paid = locked_order.total_amount
        locked_order.amount_change = Decimal("0.00")
        changed_fields.extend(["amount_paid", "amount_change"])
    if transaction_id and locked_order.transaction_id != transaction_id:
        locked_order.transaction_id = transaction_id
        changed_fields.append("transaction_id")
    if external_id and locked_order.external_id != external_id:
        locked_order.external_id = external_id
        changed_fields.append("external_id")
    if changed_fields:
        locked_order.save(update_fields=[*set(changed_fields), "updated_at"])

    return payment, sale, sale_created
