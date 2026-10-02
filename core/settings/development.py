from sys import stdout

import colorama
from colorama import Fore, Style

from .base import *

colorama.init(autoreset=True)
stdout.write(
    f"{Fore.GREEN}{Style.BRIGHT}================ Loading Development Settings =====================\n"
)

DEBUG = True
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1", "testserver"])
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    ["http://localhost", "http://127.0.0.1"],
)
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ["http://localhost:8000", "http://127.0.0.1:8000"],
)

if not env_bool("USE_DATABASE_URL", False):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "platform_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }

INSTALLED_APPS += [
    "debug_toolbar",
    "django_browser_reload",
]

MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

INTERNAL_IPS = ["127.0.0.1"]

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
MEDIA_URL = os.getenv("MEDIA_URL", "/media/")

STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"
