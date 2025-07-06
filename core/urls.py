# Import necessary modules and functions from Django
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

# Define the URL patterns for the project
urlpatterns = [
    # Admin route
    path("admin/", admin.site.urls),
    # Main application routes
    path("", include("apps.main.urls")),
    path("auth/", include("apps.authentication.urls")),
    path("customers/", include("apps.customers.urls")),
    path("supplier/", include("apps.supplier.urls")),
    path("products/", include("apps.products.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("sales/", include("apps.sales.urls")),
    path("orders/", include("apps.orders.urls")),
    path("financials/", include("apps.finance.urls")),
    path("blog/", include("apps.blog.urls")),
    # Social Authentication
    re_path(r"^oauth/", include("social_django.urls", namespace="social")),
    # Djoser authentication routes
]

# Additional URL patterns for debugging and media files in development mode
if settings.DEBUG:
    urlpatterns += [
        # Reload routes for browser refresh during development
        path("__reload__/", include("django_browser_reload.urls")),
        # Debug toolbar routes for debugging purposes
        path("__debug__/", include("debug_toolbar.urls")),
    ]

    # Serve media files during development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
