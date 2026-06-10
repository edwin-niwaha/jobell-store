from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Q
from django.http import (
    HttpResponseBadRequest,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View

from apps.authentication.decorators import (
    admin_or_manager_required,
    admin_required,
)

from .forms import (
    ContactForm,
    LoginForm,
    RegisterForm,
    UpdateProfileAllForm,
    UpdateProfileForm,
    UpdateUserForm,
)
from .models import (
    Profile,
    Contact,
)

import logging

# Configure logger
logger = logging.getLogger(__name__)


# =================================== Register User  ===================================
# class RegisterView(View):
#     form_class = RegisterForm
#     initial = {"key": "value"}
#     template_name = "accounts/register.html"

#     def dispatch(self, request, *args, **kwargs):
#         # will redirect to the home page if a user tries to access the register page while logged in
#         if request.user.is_authenticated:
#             return redirect(to="/")

#         # else process dispatch as it otherwise normally would
#         return super(RegisterView, self).dispatch(request, *args, **kwargs)

#     def get(self, request, *args, **kwargs):
#         form = self.form_class(initial=self.initial)
#         return render(request, self.template_name, {"form": form})

#     def post(self, request, *args, **kwargs):
#         form = self.form_class(request.POST)

#         if form.is_valid():
#             form.save()

#             username = form.cleaned_data.get("username")
#             messages.success(
#                 request, f"Account created for {username}", extra_tags="bg-success"
#             )

#             return redirect(to="login")

#         return render(request, self.template_name, {"form": form})


class RegisterView(View):
    form_class = RegisterForm
    initial = {"key": "value"}
    template_name = "accounts/register.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(to="/")
        return super(RegisterView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            user = form.save()  # Save the user and get the instance

            # Auto-create a Profile for the user
            Profile.objects.create(user=user)

            username = form.cleaned_data.get("username")
            messages.success(
                request, f"Account created for {username}", extra_tags="bg-success"
            )

            return redirect(to="login")

        return render(request, self.template_name, {"form": form})


# =================================== Login View ===================================


class CustomLoginView(LoginView):
    form_class = LoginForm

    def form_valid(self, form):
        user = form.get_user()

        # Check if the user has a profile, create one if it doesn't exist
        if not hasattr(user, "profile"):
            Profile.objects.create(user=user)

        remember_me = form.cleaned_data.get("remember_me")

        if not remember_me:
            # Set session expiry to 0 seconds so the session ends when the browser is closed
            self.request.session.set_expiry(0)
            self.request.session.modified = True

        return super().form_valid(form)


# =================================== Reset password View  ===================================


class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject"
    success_message = (
        "We've emailed you instructions for setting your password, "
        "if an account exists with the email you entered. You should receive them shortly."
        " If you don't receive an email, "
        "please make sure you've entered the address you registered with, and check your spam folder."
    )
    success_url = reverse_lazy("users-home")


# =================================== Change Password  ===================================


class ChangePasswordView(PasswordChangeView):
    template_name = "accounts/change_password.html"
    success_message = "Successfully Changed Your Password"
    success_url = reverse_lazy("users-home")


# =================================== Profile List View  ===================================


@login_required
@admin_required
def profile_list(request):
    # Fetch all profiles and related user data
    queryset = Profile.objects.select_related("user").all().order_by("user__username")

    # Search functionality
    search_query = request.GET.get("search", "").strip()
    if search_query:
        queryset = queryset.filter(
            Q(user__username__icontains=search_query)
            | Q(user__first_name__icontains=search_query)
            | Q(user__last_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(role__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(queryset, 50)
    page_number = request.GET.get("page")

    try:
        profiles = paginator.page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver the first page.
        profiles = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g., 9999), deliver the last page of results.
        profiles = paginator.page(paginator.num_pages)

    return render(
        request,
        "accounts/profile_list.html",  # Ensure this is the correct template name
        {
            "profiles": profiles,
            "table_title": "Profile List",
            "search_query": search_query,
            "profile_total": queryset.count(),
        },
    )


# =================================== Update Profile ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def update_profile(request, pk, template_name="accounts/profile_update.html"):
    profile = get_object_or_404(Profile.objects.select_related("user", "branch"), pk=pk)
    form_name = "Update Profile Role"

    if request.method == "POST":
        form = UpdateProfileAllForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"{profile.user.username}'s role was updated successfully.",
                extra_tags="bg-success",
            )
            return redirect("profile_list")
        messages.error(
            request,
            "Please correct the errors below.",
            extra_tags="warning",
        )
    else:
        form = UpdateProfileAllForm(instance=profile)

    context = {
        "form_name": form_name,
        "form": form,
        "profile": profile,
    }
    return render(request, template_name, context)


# =================================== Profile Update ===================================
@login_required
@transaction.atomic
def profile(request):
    try:
        profile_instance = request.user.profile
    except ObjectDoesNotExist:
        # If the user doesn't have a profile, create one
        profile_instance = Profile.objects.create(
            user=request.user, bio="", avatar="default.jpg"
        )

    if request.method == "POST":
        user_form = UpdateUserForm(request.POST, instance=request.user)
        profile_form = UpdateProfileForm(
            request.POST, request.FILES, instance=profile_instance
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(
                request, "Your profile is updated successfully", extra_tags="bg-success"
            )
            return redirect(to="users-profile")
    else:
        user_form = UpdateUserForm(instance=request.user)
        profile_form = UpdateProfileForm(instance=profile_instance)

    return render(
        request,
        "accounts/profile.html",
        {"user_form": user_form, "profile_form": profile_form},
    )


# =================================== Delete Profile ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_profile(request, pk):
    if request.method != "POST":
        messages.warning(request, "Use the delete button to remove a profile.")
        return HttpResponseRedirect(reverse("profile_list"))

    profile = get_object_or_404(Profile, id=pk)
    profile.delete()
    messages.info(request, "Profile deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("profile_list"))


# ===================================  Contact Us  ===================================
def send_contact_email(name, email):
    subject = "We've Received Your Message"

    message = (
        f"Hi {name},\n\n"
        "Thank you for reaching out to us! 🌟\n\n"
        "Your message has been received, and our team is already on it. "
        "Expect a response soon as we work to assist you promptly.\n\n"
        "In the meantime, feel free to browse our available products here:\n"
        "👉 [View Products](https://example.com/)\n\n"
        "If you have additional questions or concerns, let us know—we're here to help!\n\n"
        "Warm regards,\n"
        f"The {settings.COMPANY_NAME} Team\n"
        "Management"
    )

    from_email = getattr(settings, "EMAIL_HOST_USER", None)
    recipients = [email]  # Send to user

    # Send confirmation email to user
    try:
        send_mail(subject, message, from_email, recipients)
    except Exception as e:
        logger.error(f"Error sending email to {email}: {str(e)}")
        return False

    # Send notification email to ED_EMAIL
    if hasattr(settings, "ED_EMAIL") and settings.ED_EMAIL:
        admin_subject = f"New Contact Form Submission from {name}"
        admin_message = f"New message received from {name} ({email}). Please check the system for details."

        try:
            send_mail(admin_subject, admin_message, from_email, [settings.ED_EMAIL])
        except Exception as e:
            logger.error(f"Error sending email to {settings.ED_EMAIL}: {str(e)}")

    return True


def contact_us(request):
    form = ContactForm()

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(
                request,
                "You must be logged in to send a message.",
                extra_tags="bg-danger",
            )
            return redirect("login")  # Redirect non-logged-in users to login page

        form = ContactForm(request.POST)
        if form.is_valid():
            instance = form.save()
            email_sent = send_contact_email(instance.name, instance.email)

            if email_sent:
                messages.success(
                    request,
                    "Your message has been sent successfully. We will get back to you soon!",
                    extra_tags="bg-success",
                )
            else:
                messages.error(
                    request,
                    "Sorry, an error occurred while sending your message. Please try again later.",
                    extra_tags="bg-danger",
                )

            return HttpResponseRedirect(reverse("contact_us"))

    return render(request, "accounts/contact_us.html", {"form": form})


# =================================== Display User Feedback ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def user_feedback(request):
    feedback_queryset = Contact.objects.all()
    status = request.GET.get("status", "").strip()
    search_query = request.GET.get("search", "").strip()

    if status == "open":
        feedback_queryset = feedback_queryset.filter(is_valid=False)
    elif status == "validated":
        feedback_queryset = feedback_queryset.filter(is_valid=True)

    if search_query:
        feedback_queryset = feedback_queryset.filter(
            Q(name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(message__icontains=search_query)
        )

    paginator = Paginator(feedback_queryset, 25)
    page_number = request.GET.get("page")
    feedback = paginator.get_page(page_number)

    return render(
        request,
        "accounts/user_feedback.html",
        {
            "table_title": "User Feedback",
            "feedback": feedback,
            "search_query": search_query,
            "status": status,
            "open_feedback_count": Contact.objects.filter(is_valid=False).count(),
            "validated_feedback_count": Contact.objects.filter(is_valid=True).count(),
        },
    )


# =================================== Delete User Feedback ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_feedback(request, pk):
    if request.method != "POST":
        messages.warning(request, "Use the delete button to remove feedback.")
        return HttpResponseRedirect(reverse("user_feedback"))

    feedback = get_object_or_404(Contact, id=pk)
    feedback.delete()
    messages.info(request, "Record deleted!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("user_feedback"))


# =================================== Validate User Feedback  ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def validate_user_feedback(request, contact_id):
    user_feedback = get_object_or_404(Contact, id=contact_id)

    if request.method == "POST":
        if not user_feedback.is_valid:
            user_feedback.is_valid = True
            user_feedback.save()

            messages.success(
                request, "User validated successfully!", extra_tags="bg-success"
            )
            return HttpResponseRedirect(reverse("user_feedback"))

    return HttpResponseBadRequest("Invalid request")


def about_us(request):
    return render(request, "accounts/about_us.html")


def privacy_policy(request):
    return render(request, "accounts/privacy_policy.html")
