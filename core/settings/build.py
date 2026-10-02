"""Build static assets without database access or production credentials."""
from .base import *

DEBUG = False
SECRET_KEY = "static-assets-build-only-not-a-runtime-secret"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
STATIC_ROOT = Path(os.getenv("STATIC_BUILD_ROOT", BASE_DIR / "staticfiles"))
