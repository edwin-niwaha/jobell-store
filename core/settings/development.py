from sys import stdout

import colorama
from colorama import Fore, Style

from .base import *  # noqa: F401,F403


colorama.init(autoreset=True)
stdout.write(
    f"{Fore.GREEN}{Style.BRIGHT}================ Loading Development Settings =====================\n"
)

DEBUG = True
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1", "testserver"])  # noqa: F405
CSRF_TRUSTED_ORIGINS = env_list(  # noqa: F405
    "CSRF_TRUSTED_ORIGINS",
    ["http://localhost", "http://127.0.0.1"],
)
CORS_ALLOWED_ORIGINS = env_list(  # noqa: F405
    "CORS_ALLOWED_ORIGINS",
    ["http://localhost:8000", "http://127.0.0.1:8000"],
)

if not env_bool("USE_DATABASE_URL", False):  # noqa: F405
    DATABASES["default"] = {  # noqa: F405
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "platform_db"),  # noqa: F405
        "USER": os.getenv("DB_USER", "postgres"),  # noqa: F405
        "PASSWORD": os.getenv("DB_PASSWORD", ""),  # noqa: F405
        "HOST": os.getenv("DB_HOST", "localhost"),  # noqa: F405
        "PORT": os.getenv("DB_PORT", "5432"),  # noqa: F405
    }

INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
    "django_browser_reload",
]

MIDDLEWARE += [  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

INTERNAL_IPS = ["127.0.0.1"]

EMAIL_BACKEND = os.getenv(  # noqa: F405
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
MEDIA_URL = os.getenv("MEDIA_URL", "/media/")  # noqa: F405

STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"  # noqa: F405
