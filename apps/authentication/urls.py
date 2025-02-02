from django.urls import path, include
from django.contrib.auth import views as auth_views
from apps.authentication.forms import LoginForm
from . import views
from .views import (
    RegisterView,
    ChangePasswordView,
    CustomLoginView,
    ResetPasswordView,
)
from .viewset import LogoutView

# Define URL patterns for the application
urlpatterns = [
    # User Registration and Login
    path("register/", RegisterView.as_view(), name="users-register"),
    path(
        "login/",
        CustomLoginView.as_view(
            redirect_authenticated_user=True,
            template_name="accounts/login.html",
            authentication_form=LoginForm,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(template_name="accounts/logout.html"),
        name="logout",
    ),
    # Password Management
    path("password-reset/", ResetPasswordView.as_view(), name="password_reset"),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("password-change/", ChangePasswordView.as_view(), name="password_change"),
    # Profile Management
    path("profile/", views.profile, name="users-profile"),
    path("profile-list/", views.profile_list, name="profile_list"),
    path("profile/update/<int:pk>/", views.update_profile, name="update_profile"),
    path("profile/delete/<int:pk>/", views.delete_profile, name="delete_profile"),
    # User Feedback
    path("contact-us/", views.contact_us, name="contact_us"),
    path("feedback/", views.user_feedback, name="user_feedback"),
    path("feedback/delete/<int:pk>/", views.delete_feedback, name="delete_feedback"),
    path(
        "feedback/validate/<int:contact_id>/",
        views.validate_user_feedback,
        name="validate_user_feedback",
    ),
    path("about/", views.about_us, name="about_us"),
    path("privacy-policy/", views.privacy_policy, name="privacy_policy"),
    path("", include("djoser.urls")),  # Djoser default URLs
    path("", include("djoser.urls.jwt")),  # Djoser JWT URLs
    path("logout/", LogoutView.as_view()),  # Custom logout URL
]
