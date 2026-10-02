from .base import *

DEBUG = False
PRODUCTION = True
WHITENOISE_MANIFEST_STRICT = True

SECRET_KEY = os.environ["SECRET_KEY"]
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", [BASE_DOMAIN, f"www.{BASE_DOMAIN}"])
ALLOWED_HOSTS += ["healthcheck.railway.app"]
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    [f"https://{BASE_DOMAIN}", f"https://www.{BASE_DOMAIN}"],
)
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", [SITE_URL])

if DATABASE_URL:
    DATABASES["default"] = dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "600")),
        ssl_require=env_bool("DB_SSL_REQUIRE", True),
    )

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", True)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    STORAGES["default"] = {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    }
    MEDIA_URL = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/"

LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING")
LOGGING["root"]["level"] = LOG_LEVEL
