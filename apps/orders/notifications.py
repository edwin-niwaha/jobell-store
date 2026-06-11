import logging
from decimal import Decimal

from celery import current_app
from django.conf import settings
from django.contrib.auth import get_user_model
from django.templatetags.static import static
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from core.services.email_service import EmailServiceError, send_transactional_email


logger = logging.getLogger(__name__)


CUSTOMER_STATUS_MESSAGES = {
    "Pending": "We have received your order and our team is reviewing it.",
    "Processing": "Your order is now being prepared.",
    "Shipped": "Your order has been shipped.",
    "Out for Delivery": "Your order is out for delivery.",
    "Delivered": "Your order has been delivered. Thank you for shopping with us.",
    "Canceled": "Your order has been cancelled. Contact support if you need help.",
    "Refunded": "Your order has been refunded.",
    "Returned": "Your order has been marked as returned.",
}


def valid_recipients(*recipients):
    valid = []
    seen = set()
    for email in recipients:
        if not email:
            continue
        normalized = str(email).strip()
        if not normalized or normalized.lower() in {"none", "null", "false"}:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        valid.append(normalized)
        seen.add(key)
    return valid


def _as_iterable(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def admin_order_recipients():
    configured = valid_recipients(
        *_as_iterable(getattr(settings, "ADMIN_ORDER_EMAILS", [])),
        getattr(settings, "JOBELL_ORDER_EMAIL", ""),
    )
    if configured:
        return configured

    User = get_user_model()
    recipients = valid_recipients(
        *User.objects.filter(is_active=True, is_staff=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )
    if not recipients:
        logger.error("No admin order email recipients are configured.")
    return recipients


def _site_url():
    return getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")


def _absolute_url(path):
    if not path:
        return ""
    path = str(path)
    if path.startswith(("http://", "https://")):
        return path
    if path.startswith("//"):
        return f"https:{path}"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{_site_url()}{path}"


def _money(value):
    return value or Decimal("0")


def _item_rows(details):
    rows = []
    for detail in details:
        variant = detail.product_volume
        unit_price = detail.discounted_price if detail.discounted_price is not None else detail.price
        original_price = detail.price
        discount = Decimal("0")
        if detail.discounted_price is not None and detail.discounted_price < detail.price:
            discount = (detail.price - detail.discounted_price) * detail.quantity
        image_url = getattr(variant, "image_url", "") or getattr(detail.product, "hero_image_url", "")
        rows.append(
            {
                "detail": detail,
                "product": detail.product,
                "product_name": detail.product.name,
                "variant_label": getattr(variant, "variant_label", ""),
                "quantity": detail.quantity,
                "unit_price": unit_price,
                "original_price": original_price,
                "line_total": detail.total,
                "discount": discount,
                "image_url": _absolute_url(image_url or static("images/no-image.png")),
            }
        )
    return rows


def _order_context(order, event_title="", event_message="", old_status=None, new_status=None):
    details = list(
        order.details.select_related("product", "product_volume", "product_volume__volume")
    )
    item_rows = _item_rows(details)
    subtotal = sum((row["line_total"] for row in item_rows), Decimal("0"))
    discount_total = sum((row["discount"] for row in item_rows), Decimal("0"))
    tax_amount = _money(getattr(order, "tax_amount", Decimal("0")))
    shipping_fee = _money(order.shipping_fee)
    total = _money(order.total_amount)
    amount_paid = _money(getattr(order, "amount_paid", Decimal("0")))
    balance_due = total - amount_paid
    if balance_due < 0:
        balance_due = Decimal("0")
    customer = order.customer
    return {
        "site_name": getattr(settings, "SITE_NAME", "Jobell"),
        "company_name": getattr(settings, "COMPANY_NAME", getattr(settings, "SITE_NAME", "Jobell")),
        "support_email": getattr(settings, "SUPPORT_EMAIL", ""),
        "support_phone": getattr(settings, "SUPPORT_PHONE", ""),
        "logo_url": _absolute_url(getattr(settings, "LOGO_URL", "")),
        "placeholder_image_url": _absolute_url(static("images/no-image.png")),
        "site_url": _site_url(),
        "order": order,
        "order_number": order.id,
        "order_date": timezone.localtime(order.created_at),
        "order_url": _absolute_url(reverse("orders:order_detail_view", args=[order.id])),
        "customer": customer,
        "customer_name": customer.get_full_name() or "Customer",
        "customer_email": customer.email,
        "customer_phone": customer.mobile,
        "items": details,
        "item_rows": item_rows,
        "order_details": details,
        "all_items": details,
        "subtotal": subtotal,
        "shipping_fee": shipping_fee,
        "delivery_fee": shipping_fee,
        "tax_amount": tax_amount,
        "discount_total": discount_total,
        "discount": discount_total,
        "total": total,
        "grand_total": total,
        "amount_paid": amount_paid,
        "balance_due": balance_due,
        "payment_method": order.get_payment_method_display(),
        "payment_status": order.get_payment_status_display(),
        "delivery_address": order.delivery_address_text or getattr(customer, "address", ""),
        "shipping_method": order.get_shipping_method_display(),
        "pickup_station": order.pickup_station,
        "old_status": old_status,
        "new_status": new_status or order.status,
        "event_title": event_title,
        "event_message": event_message,
    }


def _send_order_email(
    order,
    *,
    to,
    subject,
    template_name,
    event_title,
    event_message,
    old_status=None,
    new_status=None,
):
    recipients = valid_recipients(*_as_iterable(to))
    if not recipients:
        logger.warning("Order %s email skipped; no recipients for '%s'.", order.id, subject)
        return None
    context = _order_context(
        order,
        event_title=event_title,
        event_message=event_message,
        old_status=old_status,
        new_status=new_status,
    )
    html_body = render_to_string(f"emails/orders/{template_name}.html", context)
    text_body = render_to_string(f"emails/orders/{template_name}.txt", context)
    result = send_transactional_email(
        to=recipients,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )
    logger.info("Order %s email sent to %s: %s", order.id, ", ".join(recipients), subject)
    return result


def _send_customer_email(order, *, subject, event_title, event_message, **kwargs):
    email = getattr(order.customer, "email", "")
    if not email:
        logger.warning("Order %s customer email skipped because customer email is empty.", order.id)
        return None
    return _send_order_email(
        order,
        to=email,
        subject=subject,
        template_name="order_notification",
        event_title=event_title,
        event_message=event_message,
        **kwargs,
    )


def _send_admin_email(order, *, subject, event_title, event_message, **kwargs):
    return _send_order_email(
        order,
        to=admin_order_recipients(),
        subject=subject,
        template_name="admin_order_notification",
        event_title=event_title,
        event_message=event_message,
        **kwargs,
    )


def send_order_created_emails(order):
    site_name = getattr(settings, "SITE_NAME", "Jobell")
    _send_customer_email(
        order,
        subject=f"Your {site_name} order #{order.id} has been received",
        event_title="Order received",
        event_message="Thank you for your order. We will keep you updated as it moves forward.",
    )
    payment_note = (
        "Cash on delivery order. Collect payment when the order is fulfilled."
        if order.payment_method == "cod"
        else "Online/mobile money order received. Confirm payment before fulfilment."
    )
    _send_admin_email(
        order,
        subject=f"New {site_name} order #{order.id}",
        event_title="New order",
        event_message=payment_note,
    )


def send_order_status_changed_emails(order, old_status, new_status):
    if old_status == new_status:
        logger.info("Order %s status unchanged (%s); no status email sent.", order.id, new_status)
        return
    message = CUSTOMER_STATUS_MESSAGES.get(new_status, f"Your order status is now {new_status}.")
    _send_customer_email(
        order,
        subject=f"Order #{order.id} update: {new_status}",
        event_title=f"Order {str(new_status).lower()}",
        event_message=message,
        old_status=old_status,
        new_status=new_status,
    )
    _send_admin_email(
        order,
        subject=f"Order #{order.id} status changed to {new_status}",
        event_title="Order status changed",
        event_message=f"Order status changed from {old_status or 'not set'} to {new_status}.",
        old_status=old_status,
        new_status=new_status,
    )


def send_payment_status_changed_emails(order, old_status, new_status):
    if old_status == new_status:
        logger.info("Order %s payment status unchanged (%s); no payment email sent.", order.id, new_status)
        return
    display_status = order.get_payment_status_display()
    customer_messages = {
        "completed": "We have received your payment. Your order can now move to fulfilment.",
        "pending": "Your payment is pending. We will update you when it is confirmed.",
        "failed": "Your payment was not completed. Please try again or contact support.",
    }
    _send_customer_email(
        order,
        subject=f"Payment {display_status.lower()} for order #{order.id}",
        event_title=f"Payment {display_status.lower()}",
        event_message=customer_messages.get(new_status, f"Your payment status is {display_status}."),
    )
    admin_messages = {
        "completed": "Payment has been received and recorded.",
        "pending": "Payment is pending and needs follow-up.",
        "failed": "Payment failed or was rejected. Follow up with the customer if needed.",
    }
    _send_admin_email(
        order,
        subject=f"Payment {display_status.lower()} for order #{order.id}",
        event_title="Payment update",
        event_message=admin_messages.get(new_status, f"Payment status changed from {old_status} to {new_status}."),
    )


def send_order_cancelled_emails(order):
    send_order_status_changed_emails(order, None, "Canceled")


def send_delivery_update_emails(order):
    if order.status == "Delivered":
        _send_admin_email(
            order,
            subject=f"Delivery completed for order #{order.id}",
            event_title="Delivery completed",
            event_message="This order has been marked as delivered.",
        )
    send_order_status_changed_emails(order, None, order.status)


def _celery_has_workers():
    if not getattr(settings, "ORDER_EMAIL_USE_CELERY", True):
        return False
    try:
        timeout = getattr(settings, "ORDER_EMAIL_CELERY_PING_TIMEOUT", 0.35)
        replies = current_app.control.inspect(timeout=timeout).ping()
        return bool(replies)
    except Exception:
        logger.exception("Unable to contact Celery while scheduling order email; using synchronous fallback.")
        return False


def dispatch_order_email_task(task_name, order_id, **kwargs):
    from .models import Order

    if _celery_has_workers():
        try:
            current_app.send_task(task_name, args=[order_id], kwargs=kwargs)
            logger.info("Queued %s for order %s.", task_name, order_id)
            return
        except Exception:
            logger.exception("Failed to queue %s for order %s; using synchronous fallback.", task_name, order_id)

    order = (
        Order.objects.select_related("customer", "pickup_station")
        .prefetch_related("details__product", "details__product_volume__volume")
        .get(pk=order_id)
    )
    try:
        if task_name == "orders.send_order_created_emails":
            send_order_created_emails(order)
        elif task_name == "orders.send_order_status_changed_emails":
            send_order_status_changed_emails(order, kwargs.get("old_status"), kwargs.get("new_status"))
        elif task_name == "orders.send_payment_status_changed_emails":
            send_payment_status_changed_emails(order, kwargs.get("old_status"), kwargs.get("new_status"))
        elif task_name == "orders.send_order_cancelled_emails":
            send_order_cancelled_emails(order)
        elif task_name == "orders.send_delivery_update_emails":
            send_delivery_update_emails(order)
        else:
            logger.error("Unknown order email task '%s' for order %s.", task_name, order_id)
    except EmailServiceError:
        logger.exception("Order %s email failed in synchronous fallback for %s.", order_id, task_name)
    except Exception:
        logger.exception("Unexpected order %s email failure in synchronous fallback for %s.", order_id, task_name)


def queue_order_created_emails(order_id):
    dispatch_order_email_task("orders.send_order_created_emails", order_id)


def queue_order_status_changed_emails(order_id, old_status, new_status):
    dispatch_order_email_task(
        "orders.send_order_status_changed_emails",
        order_id,
        old_status=old_status,
        new_status=new_status,
    )


def queue_payment_status_changed_emails(order_id, old_status, new_status):
    dispatch_order_email_task(
        "orders.send_payment_status_changed_emails",
        order_id,
        old_status=old_status,
        new_status=new_status,
    )


def queue_order_cancelled_emails(order_id):
    dispatch_order_email_task("orders.send_order_cancelled_emails", order_id)


def queue_delivery_update_emails(order_id):
    dispatch_order_email_task("orders.send_delivery_update_emails", order_id)
