from .base import *  # noqa: F401,F403


DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]  # noqa: F405
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", [BASE_DOMAIN, f"www.{BASE_DOMAIN}"])  # noqa: F405
CSRF_TRUSTED_ORIGINS = env_list(  # noqa: F405
    "CSRF_TRUSTED_ORIGINS",
    [f"https://{BASE_DOMAIN}", f"https://www.{BASE_DOMAIN}"],  # noqa: F405
)
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", [SITE_URL])  # noqa: F405

if DATABASE_URL:  # noqa: F405
    DATABASES["default"] = dj_database_url.config(  # noqa: F405
        default=DATABASE_URL,  # noqa: F405
        conn_max_age=int(os.getenv("DB_CONN_MAX_AGE", "600")),  # noqa: F405
        ssl_require=env_bool("DB_SSL_REQUIRE", True),  # noqa: F405
    )

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)  # noqa: F405
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)  # noqa: F405
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)  # noqa: F405
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))  # noqa: F405
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)  # noqa: F405
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", True)  # noqa: F405
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:  # noqa: F405
    STORAGES["default"] = {  # noqa: F405
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    }
    MEDIA_URL = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/"  # noqa: F405

LOG_LEVEL = os.getenv("LOG_LEVEL", "WARNING")  # noqa: F405
LOGGING["root"]["level"] = LOG_LEVEL  # noqa: F405
