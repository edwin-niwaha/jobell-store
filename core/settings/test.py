"""Isolated test settings; never use the application's configured database/email."""
from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
SECRET_KEY = "test-only-key-not-for-deployment"
SITE_URL = "https://jobellinc.com"
test_database_url = os.getenv("TEST_DATABASE_URL")  # noqa: F405
DATABASES = {"default": dj_database_url.parse(test_database_url, conn_max_age=0) if test_database_url else {  # noqa: F405
    "ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:",
}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
RESEND_API_KEY = ""
ORDER_EMAIL_USE_CELERY = False
ADMIN_ORDER_EMAILS = []
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = True
LOGGING = {"version": 1, "disable_existing_loggers": False,
           "handlers": {"console": {"class": "logging.StreamHandler"}},
           "root": {"handlers": ["console"], "level": "ERROR"}}
