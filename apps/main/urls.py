from django.urls import path

from . import views

urlpatterns = [
    # Home
    path("", views.index, name="users-home"),
    # Dashboard
    path("dashboard/sales", views.dashboard, name="dashboard"),
    path("dashboard/finance/", views.finance_dashboard, name="fin_dashboard"),
    # Chart data endpoints
    path(
        "dashboard/monthly_earnings/",
        views.monthly_earnings_view,
        name="monthly_earnings_view",
    ),
    path("dashboard/sales-data/", views.sales_data_api, name="sales-data-api"),
    path(
        "dashboard/transactions_by_account_type/",
        views.transactions_by_account_type,
        name="transactions_by_account_type",
    ),
    path(
        "dashboard/financial_period_status/",
        views.financial_period_status,
        name="financial_period_status",
    ),
    path(
        "dashboard/transaction_trends/",
        views.transaction_trends,
        name="transaction_trends",
    ),
    path("dashboard/top_accounts/", views.top_accounts, name="top_accounts"),
    path(
        "dashboard/income_vs_expenses/",
        views.income_vs_expenses,
        name="income_vs_expenses",
    ),
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
