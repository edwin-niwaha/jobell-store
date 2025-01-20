# Importing Required Libraries
import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Load environment variables from .env file
load_dotenv()

# Base directory setup
BASE_DIR = Path(__file__).resolve().parent.parent

############################### SECURITY SETTINGS ###############################

# Security settings
SECRET_KEY = os.environ.get("SECRET_KEY", "default_secret_key")

DEBUG = False  # Update to False in Production

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "jobellinc.com"]
CSRF_TRUSTED_ORIGINS = ["https://jobellinc.com"]

# SECURE_SSL_REDIRECT = True
SESSION_COOKIE_DOMAIN = ".jobellinc.com"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_DOMAIN = ".jobellinc.com"

############################### CORS CONFIGURATION ###############################
CORS_ALLOWED_ORIGINS = ["https://jobellinc.com"]

############################### APPLICATION DEFINITION ###############################

# Installed apps
INSTALLED_APPS = [
    # Django core apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "djoser",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "social_django",
    "bootstrap5",
    "formtools",
    "crispy_forms",
    "crispy_bootstrap5",
    "django.contrib.humanize",
    # Custom apps
    "apps.main",
    "apps.authentication",
    "apps.supplier",
    "apps.products",
    "apps.inventory",
    "apps.customers",
    "apps.orders",
    "apps.sales",
    "apps.finance",
    "apps.blog",
]

############################### MIDDLEWARE CONFIGURATION ###############################

# Middleware configuration
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # For handling CORS
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",  # Handles social auth exceptions
]

############################### URL AND TEMPLATE CONFIGURATION ###############################

# URL routing
ROOT_URLCONF = "core.urls"

# Template configuration
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # Add custom template directory
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                # Default context processors
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Social authentication context processors
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
                # Custom context processors
                "apps.authentication.context_processors.guest_profiles_context",
                "apps.authentication.context_processors.guest_user_feedback_context",
                "apps.authentication.context_processors.low_stock_alerts_context",
                "apps.authentication.context_processors.pending_orders_context",
            ],
        },
    },
]

# WSGI configuration
WSGI_APPLICATION = "core.wsgi.application"

# =================================== DATABASE CONFIGURATIONS ===================================
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases


############################### LOCAL DATABASE CONFIGURATION ###############################

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": os.environ.get("DB_NAME", "default_db_name"),
#         "USER": os.environ.get("DB_USER", "default_user"),
#         "PASSWORD": os.environ.get("DB_PASSWORD", "default_password"),
#         "HOST": os.environ.get("DB_HOST", "localhost"),
#         "PORT": os.environ.get("DB_PORT", "5432"),
#     }
# }


############################### ONLINE DATABASE CONFIGURATION ###############################

# Database configuration (PostgreSQL)
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", None)  # Use DATABASE_URL if provided
    )
}

############################### STATIC AND MEDIA FILES CONFIGURATION ###############################

# Local media storage
MEDIA_ROOT = BASE_DIR / "media"
LOCAL_MEDIA_URL = "/media/"

# Static files configuration
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Cloudinary storage configuration
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": CLOUDINARY_CLOUD_NAME,
    "API_KEY": CLOUDINARY_API_KEY,
    "API_SECRET": CLOUDINARY_API_SECRET,
}

DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# Cloudinary media URL online
MEDIA_URL = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/"

############################### REST FRAMEWORK AND JWT CONFIGURATION ###############################

# Django REST framework configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        # Uncomment for JWT support:
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}

# Simple JWT configuration
SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
}

############################### EMAIL CONFIGURATION ###############################

# Email backend (console for development)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Email configuration (for production)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = os.getenv("EMAIL_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_PASS")

############################### DJOSER CONFIGURATION ###############################

# Djoser configuration
DJOSER = {
    "PASSWORD_RESET_CONFIRM_URL": "auth/password/reset-password-confirmation/?uid={uid}&token={token}",
    "ACTIVATION_URL": "#/activate/{uid}/{token}",
    "SEND_ACTIVATION_EMAIL": False,
    "SERIALIZERS": {},
}

############################### GENERAL SITE SETTINGS ###############################

# General site settings
SITE_NAME = "Jobell Inc"
DOMAIN = "https://jobellinc.com"

############################### PASSWORD VALIDATION ###############################

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

############################### AUTHENTICATION BACKENDS ###############################

# Authentication backends
AUTHENTICATION_BACKENDS = (
    "social_core.backends.github.GithubOAuth2",
    "social_core.backends.google.GoogleOAuth2",
    "django.contrib.auth.backends.ModelBackend",  # Default backend
)

############################### LOCALIZATION AND TIMEZONE ###############################

# Localization and time zone settings
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True

############################### LOGIN AND SESSION SETTINGS ###############################

# Login and session settings
LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "login"


SESSION_COOKIE_AGE = 3600  # 60 * 60 seconds = 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Close session when browser closes

############################### SOCIAL AUTHENTICATION SETTINGS ###############################

# Social authentication keys (from environment variables)
SOCIAL_AUTH_GITHUB_KEY = os.getenv("GITHUB_KEY")
SOCIAL_AUTH_GITHUB_SECRET = os.getenv("GITHUB_SECRET")
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv("GOOGLE_KEY")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv("GOOGLE_SECRET")

############################### LOGGING CONFIGURATION ###############################

# Logging configuration
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": LOGS_DIR / "app.log",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

############################### DEFAULT PRIMARY KEY FIELD TYPE ###############################

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

############################### DJANGO CRISPY FORMS CONFIGURATION ###############################

# Django Crispy Forms configuration
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
