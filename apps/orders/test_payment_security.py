from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from .views import _complete_flutterwave_payment
from . import tests as ecommerce_tests
from .models import Cart, CartItem
from .services import create_order_from_cart


class PaymentVerificationTests(SimpleTestCase):
    def test_incomplete_or_mismatched_verification_never_records_payment(self):
        order = SimpleNamespace(transaction_id="JBL-reference", total_amount=Decimal("25"))
        valid = {"status": "successful", "tx_ref": "JBL-reference", "amount": "25", "currency": "UGX", "id": 999}
        for field, bad in [("tx_ref", "wrong"), ("currency", "USD"), ("id", 1000), ("amount", "NaN"), ("amount", "24"), ("amount", None)]:
            with self.subTest(field=field, value=bad), self.assertRaises(ValidationError):
                _complete_flutterwave_payment(order, {"data": {**valid, field: bad}}, 999)
        with self.assertRaises(ValidationError):
            _complete_flutterwave_payment(order, {}, 999)


class PaymentWebhookTests(TestCase):
    setUp = ecommerce_tests.EcommerceFlowTests.setUp

    @override_settings(FLUTTERWAVE_WEBHOOK_SECRET_HASH="")
    def test_unconfigured_webhook_rejects_requests(self):
        self.assertEqual(self.client.post(reverse("orders:flutterwave_webhook"), {}, content_type="application/json").status_code, 403)

    @override_settings(FLUTTERWAVE_WEBHOOK_SECRET_HASH="test-webhook-secret")
    @patch("apps.orders.views._complete_flutterwave_payment")
    @patch("apps.orders.views._verify_flutterwave_transaction")
    def test_webhook_uses_provider_verification_instead_of_posted_payment(self, verify, complete):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, volume=self.variant, quantity=1)
        order = create_order_from_cart(cart, payment_method="mobile")
        order.transaction_id = "JBL-reference"
        order.save(update_fields=["transaction_id"])
        verify.return_value = {"data": {"status": "successful", "amount": "25", "currency": "UGX", "tx_ref": "JBL-reference", "id": 999}}
        response = self.client.post(reverse("orders:flutterwave_webhook"), {"data": {"tx_ref": "JBL-reference", "id": 999, "amount": "999999"}}, content_type="application/json", HTTP_VERIF_HASH="test-webhook-secret")
        self.assertEqual(response.status_code, 200)
        verify.assert_called_once_with(999)
        self.assertEqual(complete.call_args.args[1], verify.return_value)
