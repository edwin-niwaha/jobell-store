from django.db import models
import django.utils.timezone
from apps.customers.models import Customer
from apps.products.models import Product, ProductVolume
from apps.orders.models import Order


PAYMENT_METHOD_CHOICES = [
    ("CREDIT_CARD", "Credit Card"),
    ("DEBIT_CARD", "Debit Card"),
    ("PAYPAL", "PayPal"),
    ("BANK_TRANSFER", "Bank Transfer"),
    ("CASH", "Cash"),
    ("MTN_MOBILE_MONEY", "MTN Mobile Money"),
    ("AIRTEL_MONEY", "Airtel Money"),
]

SALE_TYPE_CHOICES = [
    ("online", "Online"),
    ("offline", "Offline"),
]


# =================================== Sale model ===================================
class Sale(models.Model):
    order = models.ForeignKey(
        Order, related_name="sales", on_delete=models.SET_NULL, null=True, blank=True
    )
    sale_type = models.CharField(
        max_length=10, choices=SALE_TYPE_CHOICES, default="offline"
    )
    date_added = models.DateTimeField(default=django.utils.timezone.now)
    trans_date = models.DateField(verbose_name="Receipt Date")
    receipt_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    customer = models.ForeignKey(
        Customer, related_name="sales", on_delete=models.SET_NULL, null=True, blank=True
    )
    sub_total = models.FloatField(default=0)
    grand_total = models.FloatField(default=0)
    tax_amount = models.FloatField(default=0)
    tax_percentage = models.FloatField(default=0)
    amount_payed = models.FloatField(default=0)
    amount_change = models.FloatField(default=0)
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        default="CASH",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        db_table = "Sales"

    def __str__(self) -> str:
        return (
            "Sale ID: "
            + str(self.id)
            + " | Grand Total: "
            + str(self.grand_total)
            + " | Datetime: "
            + str(self.date_added)
        )

    def sum_items(self):
        details = SaleDetail.objects.filter(sale=self.id)
        return sum([d.quantity for d in details])

    def total_profit(self):
        """Calculate total profit for the sale."""
        profit = 0
        for item in self.items.all():
            for volume in item.product.volumes.all():
                profit += (volume.price - volume.cost) * item.quantity
        return profit

    def total_items(self):
        """Calculate total number of items sold in the sale."""
        return sum([item.quantity for item in self.items.all()])

    def total_revenue(self):
        """Return the total revenue for the sale."""
        return self.grand_total


# =================================== SaleDetail model ===================================
class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_volume = models.ForeignKey(
        ProductVolume, null=True, blank=True, on_delete=models.CASCADE
    )  # New field to track product volume
    price = models.FloatField()
    quantity = models.IntegerField()
    total_detail = models.FloatField()  # Total for the sale detail (price * quantity)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        db_table = "SaleDetails"

    def __str__(self) -> str:
        return f"Detail ID: {self.id} | Sale ID: {self.sale.id} | Quantity: {self.quantity} | Product: {self.product.name}"

    def total_item_profit(self):
        """Calculate profit for a single item."""
        if self.product_volume:
            return (
                self.product_volume.price - self.product_volume.cost
            ) * self.quantity
        return 0

    def total_item_value(self):
        """Calculate total value (price * quantity)."""
        return self.price * self.quantity

    def volume_ml(self):
        """Return the volume in ml if available."""
        return self.product_volume.volume.ml if self.product_volume else None
