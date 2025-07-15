import logging
from django.db import models
from apps.products.models import Product

logger = logging.getLogger(__name__)


class Inventory(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="inventory"
    )
    quantity = models.PositiveIntegerField(verbose_name="Stock Quantity", default=0)
    low_stock_threshold = models.PositiveIntegerField(
        default=5, verbose_name="Low Stock Threshold"
    )
    is_out_of_stock = models.BooleanField(default=False, verbose_name="Out of Stock")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    def check_stock_alerts(self):
        """Check stock levels and update stock status."""
        self.is_out_of_stock = self.quantity <= 0
        if self.quantity <= self.low_stock_threshold and not self.is_out_of_stock:
            self.send_low_stock_alert()

    def send_low_stock_alert(self):
        """Send an alert for low stock."""
        print(
            f"Low stock alert for {self.product.name}. Current stock: {self.quantity}"
        )

    def save(self, *args, **kwargs):
        logger.info(
            f"Before save - created_at: {self.created_at}, updated_at: {self.updated_at}"
        )
        self.check_stock_alerts()
        super().save(*args, **kwargs)
        logger.info(
            f"After save - created_at: {self.created_at}, updated_at: {self.updated_at}"
        )

    def __str__(self):
        return f"{self.product.name} - Stock: {self.quantity}"
