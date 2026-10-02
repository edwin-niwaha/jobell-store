from unittest.mock import patch
from django.db import OperationalError
from django.test import TestCase, override_settings
from .checks import production_services


class HealthTests(TestCase):
    def test_health_is_available_without_login_and_not_cached(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_database_failure_does_not_expose_connection_details(self):
        with patch("core.health.connection.cursor", side_effect=OperationalError("private connection details")):
            response = self.client.get("/health/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})

    @override_settings(PRODUCTION=True, SITE_URL="http://localhost", CLOUDINARY_API_KEY="", RESEND_API_KEY="", EMAIL_HOST_USER="", EMAIL_HOST_PASSWORD="")
    def test_deploy_checks_reject_development_service_settings(self):
        codes = {error.id for error in production_services(None)}
        self.assertTrue({"jobell.E001", "jobell.E003", "jobell.E004"}.issubset(codes))
