import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from apps.orders.notifications import (
    _absolute_url,
    _site_url,
    admin_order_recipients,
    valid_recipients,
)
from core.services.email_service import send_transactional_email


logger = logging.getLogger(__name__)


def _newsletter_context(subscriber):
    site_name = getattr(settings, "SITE_NAME", "Jobell")
    company_name = getattr(settings, "COMPANY_NAME", site_name)
    return {
        "site_name": site_name,
        "company_name": company_name,
        "support_email": getattr(settings, "SUPPORT_EMAIL", ""),
        "support_phone": getattr(settings, "SUPPORT_PHONE", ""),
        "logo_url": _absolute_url(getattr(settings, "LOGO_URL", "")),
        "site_url": _site_url(),
        "subscriber": subscriber,
        "subscriber_email": subscriber.email,
        "subscribed_at": timezone.localtime(subscriber.created_at),
        "event_title": "Newsletter subscription confirmed",
        "email_title": f"Welcome to {site_name}",
        "header_eyebrow": "Premium newsletter care",
        "header_badge": "Subscribed",
    }


def send_newsletter_welcome_email(subscriber):
    recipients = valid_recipients(subscriber.email)
    if not recipients:
        logger.warning("Newsletter welcome email skipped for subscriber %s; no email.", subscriber.pk)
        return None

    context = _newsletter_context(subscriber)
    html_body = render_to_string("emails/newsletter/welcome.html", context)
    text_body = render_to_string("emails/newsletter/welcome.txt", context)
    result = send_transactional_email(
        to=recipients,
        subject=f"Welcome to {context['site_name']}",
        html_body=html_body,
        text_body=text_body,
    )
    logger.info("Newsletter welcome email sent to %s.", subscriber.email)
    return result


def send_newsletter_admin_notification(subscriber):
    recipients = admin_order_recipients()
    if not recipients:
        logger.warning("Newsletter admin notification skipped; no Jobell recipients configured.")
        return None

    context = _newsletter_context(subscriber)
    context.update(
        {
            "event_title": "New newsletter subscriber",
            "email_title": "New newsletter subscriber",
            "header_badge": "Admin alert",
        }
    )
    html_body = render_to_string("emails/newsletter/admin_notification.html", context)
    text_body = render_to_string("emails/newsletter/admin_notification.txt", context)
    result = send_transactional_email(
        to=recipients,
        subject=f"New {context['site_name']} newsletter subscriber",
        html_body=html_body,
        text_body=text_body,
        reply_to=subscriber.email,
    )
    logger.info("Newsletter admin notification queued delivery for subscriber %s.", subscriber.email)
    return result


def send_newsletter_subscription_emails(subscriber):
    return {
        "welcome": send_newsletter_welcome_email(subscriber),
        "admin": send_newsletter_admin_notification(subscriber),
    }


def send_bulk_newsletter_email(subject, message, recipients):
    recipients = valid_recipients(*recipients)
    if not recipients:
        logger.warning("Bulk newsletter email skipped; no recipients for '%s'.", subject)
        return None

    result = send_transactional_email(
        to=recipients,
        subject=subject,
        html_body=message,
        text_body=message,
    )
    logger.info("Bulk newsletter email sent to %s recipients: %s", len(recipients), subject)
    return result


def queue_newsletter_subscription_emails(subscriber_id):
    from .tasks import send_newsletter_subscription_emails_task

    send_newsletter_subscription_emails_task.delay(subscriber_id)
    logger.info("Queued newsletter subscription emails for subscriber %s.", subscriber_id)


def queue_bulk_newsletter_email(subject, message, recipients):
    from .tasks import send_bulk_newsletter_email_task

    send_bulk_newsletter_email_task.delay(subject, message, list(recipients))
    logger.info("Queued bulk newsletter email to %s recipients: %s", len(recipients), subject)
