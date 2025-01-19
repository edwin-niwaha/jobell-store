from django.conf import settings
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


# =================================== customers model ===================================


class Customer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    first_name = models.CharField(max_length=50, verbose_name="First Name")
    last_name = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Last Name"
    )
    address = models.TextField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Address",  # Increased address length
    )
    email = models.EmailField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Email",  # Increased email length
    )

    tel = PhoneNumberField(
        max_length=16,
        null=True,
        blank=True,
        default="+12125552368",
        verbose_name="Telephone",
    )
    mobile = PhoneNumberField(
        max_length=16,
        null=True,
        blank=True,
        default="+12125552368",
        verbose_name="Mobile",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")

    class Meta:
        db_table = "Customers"
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        if self.user:
            return f"{self.user.username} (Customer)"
        return f"{self.first_name} {self.last_name}".strip()

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def to_select2(self):
        return {"label": self.get_full_name(), "value": self.id}
