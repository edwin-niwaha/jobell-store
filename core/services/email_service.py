import logging
from email.utils import formataddr, parseaddr

import requests
from django.conf import settings


logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Raised when a transactional email cannot be sent."""


class EmailConfigurationError(Exception):
    """Raised when email settings are incomplete."""


def _as_list(value):
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def _format_sender(from_email):
    name, address = parseaddr(from_email or "")
    if not address:
        return from_email
    return formataddr((name, address)) if name else address


def send_transactional_email(
    *,
    to,
    subject,
    html_body="",
    text_body="",
    from_email=None,
    reply_to=None,
):
    recipients = [email.strip() for email in _as_list(to) if email and email.strip()]
    if not recipients:
        logger.warning("Email skipped because no recipients were provided: %s", subject)
        return None

    api_key = getattr(settings, "RESEND_API_KEY", "")
    if not api_key:
        raise EmailConfigurationError("RESEND_API_KEY is not configured.")

    sender = _format_sender(
        from_email
        or getattr(settings, "RESEND_FROM_EMAIL", "")
        or getattr(settings, "DEFAULT_FROM_EMAIL", "")
    )
    if not sender:
        raise EmailConfigurationError("DEFAULT_FROM_EMAIL or RESEND_FROM_EMAIL is not configured.")

    payload = {
        "from": sender,
        "to": recipients,
        "subject": subject,
    }
    if html_body:
        payload["html"] = html_body
    if text_body:
        payload["text"] = text_body
    reply_to_values = _as_list(reply_to)
    if reply_to_values:
        payload["reply_to"] = reply_to_values

    api_url = getattr(settings, "RESEND_API_URL", "https://api.resend.com/emails")
    timeout = getattr(settings, "EMAIL_TIMEOUT", 10)

    try:
        response = requests.post(
            api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=timeout,
        )
        if response.status_code >= 400:
            logger.error(
                "Resend rejected email '%s' with status %s: %s",
                subject,
                response.status_code,
                response.text[:500],
            )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.exception("Failed to send transactional email '%s'.", subject)
        raise EmailServiceError("Resend email request failed.") from exc

    try:
        result = response.json()
    except ValueError:
        result = {"status_code": response.status_code}

    logger.info("Transactional email sent to %s: %s", ", ".join(recipients), subject)
    return result
