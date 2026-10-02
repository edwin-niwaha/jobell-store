"""Fail deployment checks for incomplete production service configuration."""
from urllib.parse import urlsplit
from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def production_services(app_configs, **kwargs):
    if not getattr(settings, "PRODUCTION", False):
        return []
    errors = []
    public_url = urlsplit(settings.SITE_URL)
    if public_url.scheme != "https" or not public_url.hostname or public_url.hostname in {"localhost", "127.0.0.1", "example.com"}:
        errors.append(Error("SITE_URL must be the public HTTPS storefront URL.", id="jobell.E001"))
    if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
        errors.append(Error("Production requires PostgreSQL.", id="jobell.E002"))
    if not settings.DATABASE_URL:
        errors.append(Error("Set DATABASE_URL to the production PostgreSQL service.", id="jobell.E007"))
    if not all(getattr(settings, key, "") for key in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")):
        errors.append(Error("Configure all three Cloudinary credentials for persistent production media.", id="jobell.E003"))
    if not (settings.RESEND_API_KEY or (settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)):
        errors.append(Error("Configure Resend or authenticated SMTP for transactional email.", id="jobell.E004"))
    if settings.ORDER_EMAIL_USE_CELERY and urlsplit(settings.CELERY_BROKER_URL).scheme not in {"redis", "rediss"}:
        errors.append(Error("Configure a Redis broker for the production email worker.", id="jobell.E005"))
    if any(getattr(settings, key, "") for key in ("FLUTTERWAVE_PUBLIC_KEY", "FLUTTERWAVE_SECRET_KEY", "FLUTTERWAVE_WEBHOOK_SECRET_HASH")) and not all(getattr(settings, key, "") for key in ("FLUTTERWAVE_PUBLIC_KEY", "FLUTTERWAVE_SECRET_KEY", "FLUTTERWAVE_WEBHOOK_SECRET_HASH")):
        errors.append(Error("Configure all Flutterwave keys, or leave all unset for manual payments only.", id="jobell.E006"))
    return errors
