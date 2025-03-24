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
    path(
        "testimonial/update/<int:pk>/",
        views.testimonial_update,
        name="testimonial_update",
    ),
    path(
        "testimonials/delete/<int:pk>/",
        views.testimonial_delete,
        name="testimonial_delete",
    ),
    path("subscribers/", views.subscriber_list_view, name="subscriber_list"),
    path(
        "subscribers/delete/<int:subscriber_id>/",
        views.delete_subscriber_view,
        name="delete_subscriber",
    ),
    path("send-email/", views.send_bulk_email_view, name="send_bulk_email"),
    path("reviews/", views.reviews_list_view, name="reviews_list"),
    path(
        "review/<int:review_id>/toggle_verified/",
        views.toggle_is_verified,
        name="toggle_is_verified",
    ),
    path("reviews/delete/<int:review_id>/", views.delete_review, name="delete_review"),
]
