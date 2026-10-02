import os


# Importing a specific settings module first initializes this package. Do not
# load development settings then: its mutable app/storage lists also affect base.
explicit_module = os.getenv("DJANGO_SETTINGS_MODULE")
if not explicit_module or explicit_module == __name__:
    environment = os.getenv("DJANGO_ENV", "development").strip().lower()
    if environment in {"prod", "production"}:
        from .production import *  # noqa: F401,F403
    else:
        from .development import *  # noqa: F401,F403
