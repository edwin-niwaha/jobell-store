from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.main.forms import NewsletterForm
from apps.main.models import Subscriber
from apps.main.notifications import (
    _newsletter_context,
    queue_bulk_newsletter_email,
    queue_newsletter_subscription_emails,
)
from apps.main.tasks import send_newsletter_subscription_emails_task


class NewsletterSubscriptionTests(TestCase):
    def test_newsletter_form_saves_email_and_consent(self):
        form = NewsletterForm(
            data={"email": "  CUSTOMER@Example.COM ", "consent": "on"}
        )

        self.assertTrue(form.is_valid(), form.errors)
        subscriber = form.save()

        self.assertEqual(subscriber.email, "customer@example.com")
        self.assertTrue(subscriber.consent)

    def test_newsletter_form_prevents_duplicate_email_case_insensitively(self):
        Subscriber.objects.create(email="customer@example.com", consent=True)

        form = NewsletterForm(
            data={"email": "CUSTOMER@example.com", "consent": "on"}
        )

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    @patch("apps.main.tasks.send_newsletter_subscription_emails_task.delay")
    def test_queue_newsletter_subscription_emails_uses_celery(self, delay):
        queue_newsletter_subscription_emails(12)

        delay.assert_called_once_with(12)

    @patch("apps.main.views.queue_newsletter_subscription_emails")
    def test_home_newsletter_post_saves_subscriber_and_queues_after_commit(self, queue):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("users-home"),
                {"email": "new@example.com", "consent": "on", "submit_newsletter": "1"},
            )

        self.assertEqual(response.status_code, 302)
        subscriber = Subscriber.objects.get(email="new@example.com")
        self.assertTrue(subscriber.consent)
        queue.assert_called_once_with(subscriber.id)

    @patch("apps.main.views.queue_newsletter_subscription_emails")
    def test_home_newsletter_post_without_submit_marker_still_uses_newsletter_flow(
        self, queue
    ):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("users-home"),
                {"email": "cached@example.com", "consent": "on"},
            )

        self.assertEqual(response.status_code, 302)
        subscriber = Subscriber.objects.get(email="cached@example.com")
        queue.assert_called_once_with(subscriber.id)

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
    @patch("apps.main.notifications.send_transactional_email")
    def test_subscription_task_sends_welcome_and_admin_emails_via_shared_service(
        self, send_email
    ):
        subscriber = Subscriber.objects.create(email="new@example.com", consent=True)

        send_newsletter_subscription_emails_task.run(subscriber.id)

        self.assertEqual(send_email.call_count, 2)
        welcome_call = send_email.call_args_list[0].kwargs
        admin_call = send_email.call_args_list[1].kwargs
        self.assertEqual(welcome_call["to"], ["new@example.com"])
        self.assertEqual(admin_call["to"], ["jobellinc@gmail.com"])
        self.assertIn("Welcome to Jobell", welcome_call["subject"])
        self.assertIn("New Jobell newsletter subscriber", admin_call["subject"])
        self.assertIn("background:#050505", welcome_call["html_body"])
        self.assertIn("new@example.com", admin_call["html_body"])

    @override_settings(
        SITE_NAME="Jobell",
        COMPANY_NAME="Jobell Inc",
        SITE_URL="https://jobellinc.com",
        SUPPORT_EMAIL="support@jobellinc.com",
    )
    def test_newsletter_email_templates_render_with_premium_base(self):
        subscriber = Subscriber.objects.create(email="reader@example.com", consent=True)
        context = _newsletter_context(subscriber)

        welcome_html = render_to_string("emails/newsletter/welcome.html", context)
        admin_html = render_to_string(
            "emails/newsletter/admin_notification.html",
            {**context, "event_title": "New newsletter subscriber"},
        )
        welcome_text = render_to_string("emails/newsletter/welcome.txt", context)

        self.assertIn("Premium newsletter care", welcome_html)
        self.assertIn("background:#050505", admin_html)
        self.assertIn("reader@example.com", welcome_text)

    @patch("apps.main.tasks.send_bulk_newsletter_email_task.delay")
    def test_bulk_newsletter_email_uses_celery(self, delay):
        queue_bulk_newsletter_email(
            "Offer",
            "<p>Hello</p>",
            ["reader@example.com", "reader@example.com", ""],
        )

        delay.assert_called_once_with(
            "Offer",
            "<p>Hello</p>",
            ["reader@example.com", "reader@example.com", ""],
        )
