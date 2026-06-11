import logging

from celery import shared_task

from core.services.email_service import EmailServiceError

from .notifications import (
    send_delivery_update_emails,
    send_order_cancelled_emails,
    send_order_created_emails,
    send_order_status_changed_emails,
    send_payment_status_changed_emails,
)


logger = logging.getLogger(__name__)


def _order(order_id):
    from .models import Order

    return (
        Order.objects.select_related("customer", "pickup_station")
        .prefetch_related("details__product", "details__product_volume__volume")
        .get(pk=order_id)
    )


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="orders.send_order_created_emails",
)
def send_order_created_emails_task(self, order_id):
    return send_order_created_emails(_order(order_id))


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="orders.send_order_status_changed_emails",
)
def send_order_status_changed_emails_task(self, order_id, old_status=None, new_status=None):
    return send_order_status_changed_emails(_order(order_id), old_status, new_status)


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="orders.send_payment_status_changed_emails",
)
def send_payment_status_changed_emails_task(self, order_id, old_status=None, new_status=None):
    return send_payment_status_changed_emails(_order(order_id), old_status, new_status)


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="orders.send_order_cancelled_emails",
)
def send_order_cancelled_emails_task(self, order_id):
    return send_order_cancelled_emails(_order(order_id))


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="orders.send_delivery_update_emails",
)
def send_delivery_update_emails_task(self, order_id):
    return send_delivery_update_emails(_order(order_id))


# Backwards-compatible task names used by older code paths/tests.
@shared_task(name="orders.send_order_confirmation_email")
def send_order_confirmation_email(order_id):
    return send_order_created_emails(_order(order_id))


@shared_task(name="orders.send_admin_new_order_notification")
def send_admin_new_order_notification(order_id):
    return send_order_created_emails(_order(order_id))


@shared_task(name="orders.send_order_status_email")
def send_order_status_email(order_id, old_status=None, new_status=None):
    return send_order_status_changed_emails(_order(order_id), old_status, new_status)


@shared_task(name="orders.send_payment_confirmation_email")
def send_payment_confirmation_email(order_id):
    order = _order(order_id)
    return send_payment_status_changed_emails(order, None, order.payment_status)
