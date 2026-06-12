import logging

from celery import shared_task

from core.services.email_service import EmailServiceError

from .notifications import send_contact_emails


logger = logging.getLogger(__name__)


def _contact(contact_id):
    from .models import Contact

    return Contact.objects.get(pk=contact_id)


@shared_task(
    bind=True,
    autoretry_for=(EmailServiceError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    name="authentication.send_contact_emails",
)
def send_contact_emails_task(self, contact_id):
    logger.info("Sending contact emails for feedback %s.", contact_id)
    return send_contact_emails(_contact(contact_id))

