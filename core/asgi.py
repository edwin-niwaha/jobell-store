"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from dotenv import load_dotenv

load_dotenv()

environment = os.getenv("DJANGO_ENV", "development").strip().lower()
settings_module = (
    "core.settings.production"
    if environment in {"prod", "production"}
    else "core.settings.development"
)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

application = get_asgi_application()
