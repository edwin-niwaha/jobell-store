import logging
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from core.services.email_service import (
    EmailConfigurationError,
    EmailServiceError,
    send_transactional_email,
)


logger = logging.getLogger(__name__)


def _valid_recipients(*recipients):
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


def _site_url():
    return getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")


def _absolute_url(path):
    return f"{_site_url()}{path}"


def _order_context(order):
    details = list(
        order.details.select_related("product", "product_volume", "product_volume__volume")
    )
    subtotal = sum((detail.total for detail in details), Decimal("0"))
    customer = order.customer
    order_url = _absolute_url(reverse("orders:order_detail_view", args=[order.id]))

    return {
        "site_name": getattr(settings, "SITE_NAME", "My Store"),
        "site_url": _site_url(),
        "order": order,
        "order_number": order.id,
        "order_date": timezone.localtime(order.created_at),
        "order_url": order_url,
        "customer": customer,
        "customer_name": customer.get_full_name(),
        "items": details,
        "subtotal": subtotal,
        "shipping_fee": order.shipping_fee,
        "total": order.total_amount,
        "payment_method": order.get_payment_method_display(),
        "payment_status": order.get_payment_status_display(),
        "delivery_address": order.delivery_address_text or getattr(customer, "address", ""),
        "shipping_method": order.get_shipping_method_display(),
        "pickup_station": order.pickup_station,
    }


def _send_order_template_email(order, *, subject, to, template_name, extra_context=None):
    recipients = _valid_recipients(*_as_iterable(to))
    if not recipients:
        logger.info("Order %s email skipped; no recipients for %s.", order.id, subject)
        return None

    context = _order_context(order)
    if extra_context:
        context.update(extra_context)
    html_body = render_to_string(f"emails/orders/{template_name}.html", context)
    text_body = render_to_string(f"emails/orders/{template_name}.txt", context)

    return send_transactional_email(
        to=recipients,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
    )


def _as_iterable(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _admin_order_recipients():
    configured = _valid_recipients(*getattr(settings, "ADMIN_ORDER_EMAILS", []))
    if configured:
        return configured

    User = get_user_model()
    return _valid_recipients(
        *User.objects.filter(is_active=True, is_staff=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="orders.send_email",
)
def send_email_task(self, *, to, subject, html_body="", text_body="", from_email=None, reply_to=None):
    try:
        return send_transactional_email(
            to=to,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            from_email=from_email,
            reply_to=reply_to,
        )
    except EmailConfigurationError:
        logger.exception("Email configuration error for subject '%s'.", subject)
        return None


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="orders.send_order_confirmation_email",
)
def send_order_confirmation_email(self, order_id):
    from .models import Order

    order = Order.objects.select_related("customer", "pickup_station").prefetch_related("details").get(pk=order_id)
    try:
        return _send_order_template_email(
            order,
            subject=f"Your {getattr(settings, 'SITE_NAME', 'My Store')} order #{order.id} is confirmed",
            to=order.customer.email,
            template_name="order_confirmation",
        )
    except EmailConfigurationError:
        logger.exception("Order %s confirmation email skipped due to configuration.", order_id)
        return None


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="orders.send_order_status_email",
)
def send_order_status_email(self, order_id, old_status=None, new_status=None):
    from .models import Order

    order = Order.objects.select_related("customer", "pickup_station").prefetch_related("details").get(pk=order_id)
    try:
        return _send_order_template_email(
            order,
            subject=f"Order #{order.id} status update: {new_status or order.status}",
            to=order.customer.email,
            template_name="order_status_update",
            extra_context={"old_status": old_status, "new_status": new_status or order.status},
        )
    except EmailConfigurationError:
        logger.exception("Order %s status email skipped due to configuration.", order_id)
        return None


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="orders.send_payment_confirmation_email",
)
def send_payment_confirmation_email(self, order_id):
    from .models import Order

    order = Order.objects.select_related("customer", "pickup_station").prefetch_related("details").get(pk=order_id)
    try:
        return _send_order_template_email(
            order,
            subject=f"Payment confirmed for order #{order.id}",
            to=order.customer.email,
            template_name="payment_confirmation",
        )
    except EmailConfigurationError:
        logger.exception("Order %s payment email skipped due to configuration.", order_id)
        return None


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="orders.send_admin_new_order_notification",
)
def send_admin_new_order_notification(self, order_id):
    from .models import Order

    order = Order.objects.select_related("customer", "pickup_station").prefetch_related("details").get(pk=order_id)
    try:
        return _send_order_template_email(
            order,
            subject=f"New order #{order.id} from {order.customer.get_full_name()}",
            to=_admin_order_recipients(),
            template_name="admin_new_order",
        )
    except EmailConfigurationError:
        logger.exception("Order %s admin notification skipped due to configuration.", order_id)
        return None
