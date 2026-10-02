import logging

from celery import shared_task

from core.services.email_service import EmailServiceError

from .notifications import send_bulk_newsletter_email, send_newsletter_subscription_emails


logger = logging.getLogger(__name__)


def _subscriber(subscriber_id):
    from .models import Subscriber

    return Subscriber.objects.get(pk=subscriber_id)


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="main.send_newsletter_subscription_emails",
)
def send_newsletter_subscription_emails_task(self, subscriber_id):
    logger.info("Sending newsletter subscription emails for subscriber %s.", subscriber_id)
    return send_newsletter_subscription_emails(_subscriber(subscriber_id))


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="main.send_bulk_newsletter_email",
)
def send_bulk_newsletter_email_task(self, subject, message, recipients):
    logger.info("Sending bulk newsletter email to %s recipients.", len(recipients or []))
    return send_bulk_newsletter_email(subject, message, recipients or [])
