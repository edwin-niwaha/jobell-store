import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=None):
    value = os.getenv(name)
    if not value:
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


from .branding import (  # noqa: E402
    BORDER_RADIUS,
    COMPANY_NAME,
    LOGO_URL,
    PRIMARY_COLOR,
    SECONDARY_COLOR,
    SITE_NAME,
    SUPPORT_EMAIL,
    SUPPORT_PHONE,
    TEXT_COLOR,
)


BASE_DOMAIN = os.getenv("BASE_DOMAIN", "example.com")
SITE_URL = os.getenv("SITE_URL", f"https://{BASE_DOMAIN}")

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-development-only-change-me")
DEBUG = env_bool("DEBUG", False)
# ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1", BASE_DOMAIN])
ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    ["localhost", "127.0.0.1", BASE_DOMAIN, f"www.{BASE_DOMAIN}"],
)
# CSRF_TRUSTED_ORIGINS = env_list(
#     "CSRF_TRUSTED_ORIGINS",
#     [f"https://{BASE_DOMAIN}", "http://localhost", "http://127.0.0.1"],
# )
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    [
        f"https://{BASE_DOMAIN}",
        f"https://www.{BASE_DOMAIN}",
        "http://localhost",
        "http://127.0.0.1",
    ],
)
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", [SITE_URL])


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "djoser",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "social_django",
    "bootstrap5",
    "formtools",
    "crispy_forms",
    "crispy_bootstrap5",
    "apps.common",
    "apps.main",
    "apps.authentication",
    "apps.addresses",
    "apps.supplier",
    "apps.products",
    "apps.inventory",
    "apps.customers",
    "apps.orders.apps.OrdersConfig",
    "apps.shipping",
    "apps.sales",
    "apps.finance",
    "apps.blog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.finance.middleware.CurrentUserMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
]

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
                "apps.authentication.context_processors.guest_profiles_context",
                "apps.authentication.context_processors.guest_user_feedback_context",
                "apps.authentication.context_processors.low_stock_alerts_context",
                "apps.authentication.context_processors.pending_orders_context",
                "apps.authentication.context_processors.cart_count_user_context",
                "apps.finance.context_processors.open_financial_periods",
                "apps.common.context_processors.branding",
            ],
        },
    },
]


DATABASE_URL = os.getenv("DATABASE_URL")
DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "60")),
        ssl_require=env_bool("DB_SSL_REQUIRE", False),
    )
    if DATABASE_URL
    else {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "platform_db"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}


STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = os.getenv("MEDIA_URL", "/media/")

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
    "API_KEY": CLOUDINARY_API_KEY,
    "API_SECRET": CLOUDINARY_API_SECRET,
    "MAX_FILE_SIZE": 5242880,
}


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}

SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
}

DJOSER = {
    "PASSWORD_RESET_CONFIRM_URL": "auth/password/reset-password-confirmation/?uid={uid}&token={token}",
    "ACTIVATION_URL": "#/activate/{uid}/{token}",
    "SEND_ACTIVATION_EMAIL": False,
    "SERIALIZERS": {},
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = (
    "social_core.backends.github.GithubOAuth2",
    "social_core.backends.google.GoogleOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
    "apps.authentication.pipeline.create_profile",
)

SOCIAL_AUTH_GITHUB_KEY = os.getenv("GITHUB_KEY")
SOCIAL_AUTH_GITHUB_SECRET = os.getenv("GITHUB_SECRET")
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("GOOGLE_KEY")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("GOOGLE_SECRET")


EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_PASS")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "webmaster@localhost")
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_API_URL = os.getenv("RESEND_API_URL", "https://api.resend.com/emails")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", DEFAULT_FROM_EMAIL)
ED_EMAIL = os.getenv("ED_EMAIL", "")
ADMIN_ORDER_EMAILS = env_list("ADMIN_ORDER_EMAILS", [ED_EMAIL] if ED_EMAIL else [])


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND",
    os.getenv("REDIS_RESULT_URL", "redis://localhost:6379/1"),
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = os.getenv("TIME_ZONE", "Africa/Kampala")
CELERY_ENABLE_UTC = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "60"))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "45"))
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))
CELERY_TASK_ACKS_LATE = env_bool("CELERY_TASK_ACKS_LATE", True)


LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Africa/Kampala")
USE_I18N = True
USE_TZ = True

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "login"
SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", "1209600"))
SESSION_EXPIRE_AT_BROWSER_CLOSE = env_bool("SESSION_EXPIRE_AT_BROWSER_CLOSE", False)

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "app.log",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": LOG_LEVEL,
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
