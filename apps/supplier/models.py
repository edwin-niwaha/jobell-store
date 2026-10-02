from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from phonenumber_field.modelfields import PhoneNumberField
import phonenumbers


class Supplier(models.Model):
    name = models.CharField(max_length=255, verbose_name="Supplier Name")
    contact_name = models.CharField(max_length=255, verbose_name="Contact Name")
    email = models.EmailField(verbose_name="Email Address")
    phone = PhoneNumberField(
        null=True, blank=True, default="+12125552368", verbose_name="Telephone"
    )
    address = models.CharField(max_length=255, verbose_name="Address")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Created At")

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="supplier_name_idx"),
            models.Index(fields=["email"], name="supplier_email_idx"),
            models.Index(fields=["created_at"], name="supplier_created_idx"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        self.validate_name()
        self.validate_email()
        self.validate_phone()

    def validate_name(self):
        if not self.name.strip():
            raise ValidationError("Supplier name cannot be empty.")

    def validate_email(self):
        if not self.email:
            raise ValidationError("Email address cannot be empty.")

    def validate_phone(self):
        if self.phone:
            try:
                parsed_phone = phonenumbers.parse(str(self.phone), None)
                if not phonenumbers.is_valid_number(parsed_phone):
                    raise ValidationError("Phone number is invalid.")
            except phonenumbers.NumberParseException:
                raise ValidationError("Phone number could not be parsed.")
