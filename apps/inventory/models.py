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

    class Meta:
        ordering = ["product__name"]
        indexes = [
            models.Index(fields=["quantity"], name="inventory_quantity_idx"),
            models.Index(fields=["is_out_of_stock", "quantity"], name="inventory_stock_status_idx"),
            models.Index(fields=["updated_at"], name="inventory_updated_idx"),
        ]

    @property
    def low_stock(self):
        return not self.is_out_of_stock and self.quantity <= self.low_stock_threshold

    def check_stock_alerts(self):
        """Check stock levels and update stock status."""
        self.is_out_of_stock = self.quantity <= 0
        if self.quantity <= self.low_stock_threshold and not self.is_out_of_stock:
            self.send_low_stock_alert()

    def send_low_stock_alert(self):
        """Send an alert for low stock."""
        logger.warning(
            "Low stock alert for %s. Current stock: %s",
            self.product.name,
            self.quantity,
        )

    def save(self, *args, **kwargs):
        self.check_stock_alerts()
        super().save(*args, **kwargs)
        variants = self.product.productvolume_set.filter(is_active=True)
        if variants.count() == 1:
            variants.update(stock_quantity=self.quantity)

    def __str__(self):
        return f"{self.product.name} - Stock: {self.quantity}"
