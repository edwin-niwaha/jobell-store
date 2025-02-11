from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordChangeView, PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
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
class RegisterView(View):
    form_class = RegisterForm
    initial = {"key": "value"}
    template_name = "accounts/register.html"

    def dispatch(self, request, *args, **kwargs):
        # will redirect to the home page if a user tries to access the register page while logged in
        if request.user.is_authenticated:
            return redirect(to="/")

        # else process dispatch as it otherwise normally would
        return super(RegisterView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            form.save()

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
        remember_me = form.cleaned_data.get("remember_me")

        if not remember_me:
            # set session expiry to 0 seconds. So it will automatically close the session after the browser is closed.
            self.request.session.set_expiry(0)

            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
        return super(CustomLoginView, self).form_valid(form)


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
    search_query = request.GET.get("search")
    if search_query:
        queryset = queryset.filter(user__username__icontains=search_query)

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
        },
    )


# =================================== Update Profile ===================================
@login_required
@transaction.atomic
def update_profile(request, pk, template_name="accounts/profile_update.html"):
    profile = get_object_or_404(Profile, pk=pk)

    if request.method == "POST":
        form = UpdateProfileAllForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Updated successfully!", extra_tags="bg-success")
            return redirect("profile_list")
    else:
        form = UpdateProfileAllForm(instance=profile)

    # Render the form in the template
    context = {"form_name": "Update Profile", "form": form}
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
    profile = Profile.objects.get(id=pk)
    profile.delete()
    messages.info(request, "Profile deleted successfully!", extra_tags="bg-danger")
    return HttpResponseRedirect(reverse("profile_list"))


# ===================================  Contact Us  ===================================
@transaction.atomic
def send_contact_email(name, email):

    subject = "We've Received Your Message"

    message = (
        f"Hi {name},\n\n"
        "Thank you for reaching out to us! 🌟\n\n"
        "Your message has been received, and our team is already on it. "
        "Expect a response soon as we work to assist you promptly.\n\n"
        "In the meantime, feel free to browse our available products here:\n"
        "👉 [View Products](https://jobellinc.com/)\n\n"
        "If you have additional questions or concerns, let us know—we're here to help!\n\n"
        "Warm regards,\n"
        "The Jobell Inc. Team\n"
        "Management"
    )
    from_email = getattr(settings, "EMAIL_HOST_USER", None)
    to = [email]

    try:
        send_mail(subject, message, from_email, to)
        return True
    except Exception as e:
        logger.error(f"Error sending email to {email}: {str(e)}")
        return False


def contact_us(request):

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            instance = form.save()

            # Attempt to send the confirmation email
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

            # Redirect to the contact page
            return HttpResponseRedirect(reverse("contact_us"))
    else:
        form = ContactForm()

    return render(request, "accounts/contact_us.html", {"form": form})


# =================================== Display User Feedback ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def user_feedback(request):
    feedback = Contact.objects.all()
    return render(
        request,
        "accounts/user_feedback.html",
        {"table_title": "User Feedback", "feedback": feedback},
    )


# =================================== Delete User Feedback ===================================
@login_required
@admin_or_manager_required
@transaction.atomic
def delete_feedback(request, pk):
    feedback = Contact.objects.get(id=pk)
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
