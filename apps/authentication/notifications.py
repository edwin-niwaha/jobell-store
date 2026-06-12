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


def _contact_context(contact):
    site_name = getattr(settings, "SITE_NAME", "Jobell")
    return {
        "site_name": site_name,
        "company_name": getattr(settings, "COMPANY_NAME", site_name),
        "support_email": getattr(settings, "SUPPORT_EMAIL", ""),
        "support_phone": getattr(settings, "SUPPORT_PHONE", ""),
        "logo_url": _absolute_url(getattr(settings, "LOGO_URL", "")),
        "site_url": _site_url(),
        "contact": contact,
        "contact_name": contact.name,
        "contact_email": contact.email,
        "contact_message": contact.message,
        "submitted_at": timezone.localtime(contact.created_at),
        "event_title": "Message received",
        "email_title": f"We received your message | {site_name}",
        "header_eyebrow": "Premium support care",
        "header_badge": "Received",
    }


def send_contact_confirmation_email(contact):
    recipients = valid_recipients(contact.email)
    if not recipients:
        logger.warning("Contact confirmation skipped for feedback %s; no recipient.", contact.pk)
        return None

    context = _contact_context(contact)
    html_body = render_to_string("emails/contact/confirmation.html", context)
    text_body = render_to_string("emails/contact/confirmation.txt", context)
    result = send_transactional_email(
        to=recipients,
        subject=f"We received your message | {context['site_name']}",
        html_body=html_body,
        text_body=text_body,
    )
    logger.info("Contact confirmation email sent for feedback %s to %s.", contact.pk, contact.email)
    return result


def send_contact_admin_notification(contact):
    recipients = admin_order_recipients()
    if not recipients:
        logger.warning("Contact admin notification skipped for feedback %s; no Jobell recipients.", contact.pk)
        return None

    context = _contact_context(contact)
    context.update(
        {
            "event_title": "New contact message",
            "email_title": "New contact message",
            "header_badge": "Admin alert",
        }
    )
    html_body = render_to_string("emails/contact/admin_notification.html", context)
    text_body = render_to_string("emails/contact/admin_notification.txt", context)
    result = send_transactional_email(
        to=recipients,
        subject=f"New {context['site_name']} contact message from {contact.name}",
        html_body=html_body,
        text_body=text_body,
        reply_to=contact.email,
    )
    logger.info("Contact admin notification sent for feedback %s.", contact.pk)
    return result


def send_contact_emails(contact):
    return {
        "confirmation": send_contact_confirmation_email(contact),
        "admin": send_contact_admin_notification(contact),
    }


def queue_contact_emails(contact_id):
    from .tasks import send_contact_emails_task

    send_contact_emails_task.delay(contact_id)
    logger.info("Queued contact emails for feedback %s.", contact_id)
