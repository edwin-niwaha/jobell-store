import os


def _settings_module_for_environment():
    explicit_module = os.getenv("DJANGO_SETTINGS_MODULE")
    if explicit_module and explicit_module != __name__:
        return explicit_module

    environment = os.getenv("DJANGO_ENV", "development").strip().lower()
    if environment in {"prod", "production"}:
        return "core.settings.production"
    return "core.settings.development"


module = _settings_module_for_environment()

if module.endswith(".production"):
    from .production import *  # noqa: F401,F403
else:
    from .development import *  # noqa: F401,F403
