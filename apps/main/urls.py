from django.urls import path

from . import views

urlpatterns = [
    # Home
    path("", views.index, name="users-home"),
    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    path(
        "dashboard/monthly_earnings/",
        views.monthly_earnings_view,
        name="monthly_earnings_view",
    ),
    path("dashboard/sales-data/", views.sales_data_api, name="sales-data-api"),
    path("testimonials/", views.testimonials_view, name="testimonials"),
]
