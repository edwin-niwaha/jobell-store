from functools import wraps

from django.shortcuts import render


def role_required(roles):
    """Decorator to require one or more roles."""
    if isinstance(roles, str):
        roles = [roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user_profile = getattr(request.user, "profile", None)
            if not user_profile or user_profile.role not in roles:
                return render(request, "accounts/errors/403.html", status=403)
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def admin_required(view_func):
    """Decorator to require the user to be an administrator."""
    return role_required("administrator")(view_func)


def admin_or_manager_required(view_func):
    """Decorator to require the user to be an administrator or manager."""
    return role_required(["administrator", "manager"])(view_func)


def admin_or_manager_or_staff_required(view_func):
    """Decorator to require the user to be either an administrator, manager, or staff."""
    return role_required(["administrator", "manager", "staff"])(view_func)
