"""Read-only WhatsApp enquiry summaries; no orders or payments are created."""
from decimal import Decimal
from urllib.parse import quote, urlencode, urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from apps.products.models import Product, ProductVolume

from .models import Cart
from .services import _validate_cart_items, validate_purchase_item


def money(value):
    return f"UGX {value:,.0f}"


def product_link(request, product):
    path = reverse("orders:product_detail", args=[product.uuid])
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    domain = getattr(settings, "BASE_DOMAIN", "")
    local_hosts = {"localhost", "127.0.0.1", "::1", "example.com"}
    parsed = urlsplit(site_url)
    if parsed.scheme in {"http", "https"} and parsed.hostname and parsed.hostname not in local_hosts:
        return site_url + path
    if domain and domain not in local_hosts:
        return f"https://{domain}" + path
    return request.build_absolute_uri(path)


@require_GET
def review(request, product_uuid=None):
    lines, errors = [], []
    back_url = reverse("orders:cart")
    try:
        if product_uuid:
            product = get_object_or_404(Product, uuid=product_uuid)
            back_url = reverse("orders:product_detail", args=[product.uuid])
            try:
                variant_id = int(request.GET.get("volume_id", ""))
                quantity = int(request.GET.get("quantity", ""))
            except (ValueError, TypeError):
                raise ValidationError("Choose a fragrance option and a valid whole-number quantity.")
            variant = ProductVolume.objects.select_related("volume").filter(pk=variant_id, product=product).first()
            if not variant:
                raise ValidationError("Choose an available fragrance option for this product.")
            validate_purchase_item(product, variant, quantity)
            back_url += "?" + urlencode({"volume_id": variant.pk, "quantity": quantity})
            purchases = [(product, variant, quantity)]
        else:
            cart = None
            if request.user.is_authenticated:
                cart = Cart.objects.filter(user=request.user, session_key=None).first()
            elif request.session.session_key:
                cart = Cart.objects.filter(user=None, session_key=request.session.session_key).first()
            if not cart:
                raise ValidationError("Your cart is empty. Add a fragrance before ordering on WhatsApp.")
            purchases = [(item.product, item.volume, item.quantity) for item in _validate_cart_items(cart)]
        for product, variant, quantity in purchases:
            price = variant.get_discounted_price()
            lines.append({"product": product, "variant": variant, "quantity": quantity,
                          "price": price, "total": price * quantity,
                          "quantity_limit": min(variant.available_quantity, variant.max_quantity_per_order or variant.available_quantity),
                          "url": product_link(request, product)})
    except ValidationError as exc:
        errors = exc.messages
    except ValueError:
        errors = ["Your cart is empty. Add a fragrance before ordering on WhatsApp."]

    subtotal = sum((line["total"] for line in lines), Decimal("0"))
    message_parts = ["🛍️ *JOBELL STORE | ORDER ENQUIRY*", "Hello Jobell Store! 👋\nI’d love to order these fragrances:"]
    for index, line in enumerate(lines, 1):
        message_parts.append(
            f'{index}. *{line["product"].name}*\n'
            f'{line["variant"].variant_label}\n'
            f'Quantity: {line["quantity"]}\n'
            f'Unit price: {money(line["price"])}\n'
            f'Total: {money(line["total"])}\n'
            f'🔗 View product:\n{line["url"]}'
        )
    quantity = sum(line["quantity"] for line in lines)
    message_parts.extend([
        f'🧾 *ORDER SUMMARY*\nItems: {quantity}\n*Subtotal: {money(subtotal)}*',
        '🚚 *DELIVERY & PAYMENT*\nDelivery: To be confirmed\nPlease confirm availability, delivery charges, and payment options.',
        'Thank you! ✨',
    ])
    message = "\n\n".join(message_parts)
    response = render(request, "orders/whatsapp_review.html", {
        "lines": lines, "errors": errors, "subtotal": subtotal, "back_url": back_url,
        "order_message": message, "whatsapp_url": "https://wa.me/256777337491?text=" + quote(message, safe=""),
        "product_order": bool(product_uuid),
    })
    response["Cache-Control"] = "no-store"
    return response
