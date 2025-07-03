from threading import local

_thread_locals = local()


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store the current user in thread-local storage
        _thread_locals.user = getattr(request, "user", None)
        response = self.get_response(request)
        # Clean up after the request
        _thread_locals.user = None
        return response


def get_current_user():
    # Retrieve the current user from thread-local storage
    return getattr(_thread_locals, "user", None)
