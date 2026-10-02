from django.conf import settings


def branding(request):
    branding_config = {
        "site_name": settings.SITE_NAME,
        "company_name": settings.COMPANY_NAME,
        "primary_color": settings.PRIMARY_COLOR,
        "secondary_color": settings.SECONDARY_COLOR,
        "text_color": settings.TEXT_COLOR,
        "border_radius": settings.BORDER_RADIUS,
        "logo_url": settings.LOGO_URL,
        "support_email": settings.SUPPORT_EMAIL,
        "support_phone": settings.SUPPORT_PHONE,
        "site_url": settings.SITE_URL,
    }
    return {
        **branding_config,
        "branding": branding_config,
    }
