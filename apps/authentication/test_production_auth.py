from urllib.parse import parse_qs, urlsplit

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse


class AuthenticationCompatibilityTests(TestCase):
    def test_existing_registration_and_jwt_endpoints(self):
        credentials = {"username": "api-buyer", "password": "buyer-Test-Password-729!"}
        response = self.client.post("/auth/users/", {**credentials, "email": "buyer@example.com"}, content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        response = self.client.post("/auth/jwt/create/", credentials, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        tokens = response.json()
        self.assertTrue(tokens["refresh"])
        response = self.client.get("/auth/users/me/", HTTP_AUTHORIZATION="Bearer " + tokens["access"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], credentials["username"])

    def test_inactive_user_cannot_get_jwt(self):
        User.objects.create_user(username="inactive", password="buyer-Test-Password-729!", is_active=False)
        response = self.client.post("/auth/jwt/create/", {"username": "inactive", "password": "buyer-Test-Password-729!"}, content_type="application/json")
        self.assertEqual(response.status_code, 401)

    @override_settings(SOCIAL_AUTH_GOOGLE_OAUTH2_KEY="test-client", SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET="test-secret")
    def test_google_login_requires_csrf_protected_post_and_preserves_next(self):
        client = Client(enforce_csrf_checks=True)
        begin = reverse("social:begin", args=["google-oauth2"])
        response = client.get(reverse("login"), {"next": "/orders/checkout/"})
        self.assertContains(response, f'method="post" action="{begin}"')
        self.assertEqual(client.get(begin).status_code, 405)
        self.assertEqual(client.post(begin).status_code, 403)
        token = client.cookies["csrftoken"].value
        response = client.post(begin, {"csrfmiddlewaretoken": token, "next": "/orders/checkout/"})
        self.assertEqual(response.status_code, 302)
        location = urlsplit(response["Location"])
        self.assertEqual(location.hostname, "accounts.google.com")
        self.assertTrue(parse_qs(location.query)["state"])
        self.assertEqual(client.session["next"], "/orders/checkout/")

    @override_settings(SOCIAL_AUTH_GOOGLE_OAUTH2_KEY="", SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET="")
    def test_unconfigured_google_login_is_hidden(self):
        self.assertNotContains(self.client.get(reverse("login")), "Continue with Google")
