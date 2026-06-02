from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property

from apps.customers.models import Customer
from apps.products.models import Product, ProductVolume


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts",
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        help_text="Session key for anonymous users",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "updated_at"], name="cart_user_updated_idx"),
            models.Index(fields=["session_key"], name="cart_session_idx"),
            models.Index(fields=["updated_at"], name="cart_updated_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(user__isnull=False),
                name="unique_cart_per_user",
            ),
            models.UniqueConstraint(
                fields=["session_key"],
                condition=Q(session_key__isnull=False),
                name="unique_cart_per_session",
            ),
        ]

    def __str__(self):
        if self.user:
            return f"Cart of {self.user.username}"
        return f"Anonymous Cart ({self.session_key})"

    def get_total_price(self):
        return sum((item.get_total_price() for item in self.items.select_related("volume")), Decimal("0"))

    def checkout(self, payment_method, total_amount):
        if not self.user:
            raise ValueError("Cannot checkout an anonymous cart. Please log in.")
        customer, _ = Customer.objects.get_or_create(
            user=self.user,
            defaults={
                "first_name": self.user.first_name or self.user.username,
                "last_name": self.user.last_name,
                "email": self.user.email,
            },
        )
        order = Order.objects.create(
            customer=customer,
            total_amount=total_amount,
            payment_method=payment_method,
            status="Pending",
        )
        for item in self.items.select_related("product", "volume"):
            OrderDetail.objects.create(
                order=order,
                product=item.product,
                product_volume=item.volume,
                quantity=item.quantity,
                price=item.volume.effective_price,
            )
        self.items.all().delete()
        return order


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    volume = models.ForeignKey(ProductVolume, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["cart", "product"], name="cartitem_cart_product_idx"),
            models.Index(fields=["updated_at"], name="cartitem_updated_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["cart", "volume"], name="unique_cart_variant"),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.volume.variant_label} (x{self.quantity})"

    def get_total_price(self):
        return self.volume.get_discounted_price() * self.quantity


class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Out for Delivery", "Out for Delivery"),
        ("Delivered", "Delivered"),
        ("Canceled", "Canceled"),
        ("Refunded", "Refunded"),
        ("Returned", "Returned"),
    ]
    PAYMENT_METHOD_CHOICES = [("cod", "Cash on Delivery"), ("mobile", "Mobile Money")]
    PAYMENT_STATUS_CHOICES = [("pending", "Pending"), ("completed", "Completed"), ("failed", "Failed")]
    SHIPPING_METHOD_CHOICES = [
        ("delivery", "Door Delivery"),
        ("pickup", "Pickup Station"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default="Pending")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cod")
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_change = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transaction_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending")
    external_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    mobile_money_number = models.CharField(max_length=20, blank=True, null=True)
    shipping_method = models.CharField(
        max_length=20,
        choices=SHIPPING_METHOD_CHOICES,
        default="delivery",
        db_index=True,
    )
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    delivery_address_text = models.TextField(blank=True)
    delivery_region = models.CharField(max_length=30, blank=True, db_index=True)
    pickup_station = models.ForeignKey(
        "shipping.PickupStation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "created_at"], name="order_customer_created_idx"),
            models.Index(fields=["status", "created_at"], name="order_status_created_idx"),
            models.Index(fields=["payment_status", "created_at"], name="ord_paystat_cr_idx"),
            models.Index(fields=["payment_method", "created_at"], name="ord_paymeth_cr_idx"),
            models.Index(fields=["shipping_method", "created_at"], name="ord_shipmeth_cr_idx"),
            models.Index(fields=["created_at"], name="order_created_idx"),
        ]

    def __str__(self):
        return f"Order {self.id} by {self.customer.get_full_name()}"

    def calculate_totals(self, save=True):
        subtotal = sum((detail.total for detail in self.details.all()), Decimal("0"))
        self.total_amount = subtotal + self.tax_amount + self.shipping_fee
        self.amount_change = self.amount_paid - self.total_amount
        if save:
            self.save(update_fields=["total_amount", "amount_change", "updated_at"])
        return self.total_amount


class OrderDetail(models.Model):
    order = models.ForeignKey(Order, related_name="details", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_volume = models.ForeignKey(ProductVolume, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order_id", "id"]
        indexes = [
            models.Index(fields=["order", "product"], name="orderdetail_order_product_idx"),
            models.Index(fields=["product", "created_at"], name="odet_prod_cr_idx"),
        ]

    @property
    def total(self):
        return self.quantity * (self.discounted_price if self.discounted_price is not None else self.price)

    @cached_property
    def has_discount(self):
        return self.discounted_price is not None and self.discounted_price < self.price

    def save(self, *args, **kwargs):
        if self.discounted_price is None and self.product_volume.discount_value:
            self.discounted_price = self.product_volume.get_discounted_price()
        super().save(*args, **kwargs)


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlists")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-added_at"]
        indexes = [
            models.Index(fields=["user", "added_at"], name="wishlist_user_added_idx"),
            models.Index(fields=["product", "added_at"], name="wishlist_product_added_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "product"], name="unique_user_product_wishlist"),
        ]

    def __str__(self):
        return f"{self.user.username}'s Wishlist - {self.product.name}"
