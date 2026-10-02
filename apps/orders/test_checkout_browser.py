"""Optional browser regression checks against an isolated Django test database.

Requires Playwright in NODE_PATH and its Chromium browser; no project dependency.
"""
import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

from apps.shipping.models import PickupStation

from . import tests as ecommerce_tests
from .models import Cart, CartItem, Order


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', ORDER_EMAIL_USE_CELERY=False, ADMIN_ORDER_EMAILS=[], RESEND_API_KEY='')
class CheckoutBrowserTests(StaticLiveServerTestCase):
    setUp = ecommerce_tests.EcommerceFlowTests.setUp

    def check_order(self, method, width):
        node = shutil.which('node')
        if not node or not os.environ.get('NODE_PATH'):
            self.skipTest('Browser checks require Node and Playwright in NODE_PATH')
        session = self.client.session
        session.save()
        cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=cart, product=self.product, volume=self.variant, quantity=1)
        station = PickupStation.objects.create(name='Browser pickup', city='Kampala', area='Central', address='Test address')
        # Browser tests exercise ordering only; never queue or send notifications.
        with patch('apps.orders.notifications.dispatch_order_email_task'):
            result = subprocess.run([
                node, str(Path(__file__).with_name('checkout_browser_check.cjs')),
                self.live_server_url, settings.SESSION_COOKIE_NAME, session.session_key,
                str(station.pk), method, str(width)
            ], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)
        print(result.stdout + result.stderr, flush=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        order = Order.objects.get()
        self.assertEqual(order.payment_method, method)
        self.assertEqual(order.payment_status, 'pending')
        self.assertFalse(cart.items.exists())
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 5)
        self.assertFalse(order.payments.exists())
        if method == 'mobile':
            self.assertEqual(order.transaction_id, 'TEST-MM-REFERENCE')

    def test_phone_cod_after_enter_and_browser_back(self):
        self.check_order('cod', 390)

    def test_phone_mobile_money(self):
        self.check_order('mobile', 320)

    def test_desktop_cod(self):
        self.check_order('cod', 1440)
