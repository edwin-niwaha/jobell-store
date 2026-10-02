from unittest.mock import patch

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.authentication.models import Contact
from apps.authentication.notifications import _contact_context, queue_contact_emails
from apps.authentication.tasks import send_contact_emails_task


class AccountPageLayoutTests(TestCase):
    def test_account_pages_render_without_authentication(self):
        for name in ("login", "users-register", "password_reset", "contact_us"):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "account_forms.css")

    def test_registration_failure_preserves_next_destination_and_fields(self):
        response = self.client.post(reverse("users-register"), {"first_name": "Buyer", "email": "bad-email", "next": "/orders/checkout/"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="next" value="/orders/checkout/"')
        self.assertContains(response, 'value="Buyer"')
        self.assertContains(response, "Enter a valid email address.")
        self.assertEqual(User.objects.count(), 0)

    def test_reset_failure_preserves_email_and_shows_error(self):
        response = self.client.post(reverse("password_reset"), {"email": "bad-email"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="bad-email"')
        self.assertContains(response, "Enter a valid email address.")

    def test_contact_page_explains_login_requirement_before_submission(self):
        response = self.client.get(reverse("contact_us"))
        self.assertContains(response, "Sign in to send a message through this form.")
        self.assertContains(response, "next=/auth/contact-us/")
        self.assertNotContains(response, 'id="contact-form"')


class ContactEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="password123",
        )

    @patch("apps.authentication.tasks.send_contact_emails_task.delay")
    def test_queue_contact_emails_uses_celery(self, delay):
        queue_contact_emails(17)

        delay.assert_called_once_with(17)

    @patch("apps.authentication.views.queue_contact_emails")
    def test_contact_form_saves_feedback_and_queues_email_after_commit(self, queue):
        self.client.login(username="customer", password="password123")

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("contact_us"),
                {
                    "name": "Customer",
                    "email": "customer@example.com",
                    "message": "Please help with my order.",
                },
            )

        self.assertEqual(response.status_code, 302)
        contact = Contact.objects.get(email="customer@example.com")
        self.assertEqual(contact.name, "Customer")
        queue.assert_called_once_with(contact.id)

    @override_settings(
        ADMIN_ORDER_EMAILS=["jobellinc@gmail.com"],
        JOBELL_ORDER_EMAIL="jobellinc@gmail.com",
        ED_EMAIL="",
        SITE_NAME="Jobell",
        COMPANY_NAME="Jobell Inc",
        SITE_URL="https://jobellinc.com",
        LOGO_URL="/static/images/no-image.png",
        SUPPORT_EMAIL="support@jobellinc.com",
        SUPPORT_PHONE="+256 777 337491",
    )
    @patch("apps.authentication.notifications.send_transactional_email")
    def test_contact_task_sends_confirmation_and_admin_emails_via_shared_service(
        self, send_email
    ):
        contact = Contact.objects.create(
            name="Customer",
            email="customer@example.com",
            message="Please help with my order.",
        )

        send_contact_emails_task.run(contact.id)

        self.assertEqual(send_email.call_count, 2)
        confirmation_call = send_email.call_args_list[0].kwargs
        admin_call = send_email.call_args_list[1].kwargs
        self.assertEqual(confirmation_call["to"], ["customer@example.com"])
        self.assertEqual(admin_call["to"], ["jobellinc@gmail.com"])
        self.assertIn("We received your message", confirmation_call["subject"])
        self.assertIn("New Jobell contact message", admin_call["subject"])
        self.assertIn("background:#050505", confirmation_call["html_body"])
        self.assertIn("Please help with my order.", admin_call["html_body"])

    @override_settings(
        SITE_NAME="Jobell",
        COMPANY_NAME="Jobell Inc",
        SITE_URL="https://jobellinc.com",
        SUPPORT_EMAIL="support@jobellinc.com",
    )
    def test_contact_email_templates_render_with_premium_base(self):
        contact = Contact.objects.create(
            name="Customer",
            email="customer@example.com",
            message="Please help with my order.",
        )
        context = _contact_context(contact)

        confirmation_html = render_to_string("emails/contact/confirmation.html", context)
        admin_html = render_to_string(
            "emails/contact/admin_notification.html",
            {**context, "event_title": "New contact message"},
        )
        confirmation_text = render_to_string("emails/contact/confirmation.txt", context)

        self.assertIn("Premium support care", confirmation_html)
        self.assertIn("background:#050505", admin_html)
        self.assertIn("customer@example.com", confirmation_text)
