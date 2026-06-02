from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class CustomerAddress(TimeStampedModel):
    class Region(models.TextChoices):
        KAMPALA_AREA = "kampala_area", "Kampala Area"
        ENTEBBE_AREA = "entebbe_area", "Entebbe Area"
        CENTRAL_REGION = "central_region", "Central Region"
        EASTERN_REGION = "eastern_region", "Eastern Region"
        NORTHERN_REGION = "northern_region", "Northern Region"
        WESTERN_REGION = "western_region", "Western Region"
        REST_OF_KAMPALA = "rest_of_kampala", "Rest of Kampala"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    street_name = models.CharField(
        max_length=255,
        verbose_name="Street Name / Building Number / Apartment",
    )
    city = models.CharField(max_length=100, db_index=True)
    area = models.CharField(max_length=100, blank=True, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True)
    additional_telephone = models.CharField(max_length=20, blank=True)
    additional_information = models.TextField(blank=True)
    region = models.CharField(
        max_length=30,
        choices=Region.choices,
        default=Region.KAMPALA_AREA,
        db_index=True,
    )
    is_default = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        verbose_name = "Customer Address"
        verbose_name_plural = "Customer Addresses"
        indexes = [
            models.Index(fields=["user", "-is_default", "-created_at"]),
            models.Index(fields=["user", "city"]),
            models.Index(fields=["user", "area"], name="address_user_area_idx"),
            models.Index(fields=["user", "region"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_default=True),
                name="unique_default_address_per_user",
            ),
        ]

    def __str__(self):
        identifier = (
            getattr(self.user, "email", None)
            or getattr(self.user, "username", str(self.user))
        )
        return f"{identifier} - {self.city}"

    @property
    def single_line(self):
        parts = [self.street_name, self.area, self.city, self.get_region_display()]
        return ", ".join(part for part in parts if part)

    def clean(self):
        super().clean()
        if (
            self.phone_number
            and self.additional_telephone
            and self.phone_number == self.additional_telephone
        ):
            raise ValidationError(
                {
                    "additional_telephone": (
                        "Additional telephone must be different from phone number."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if self.is_default:
            type(self).objects.filter(user=self.user).exclude(pk=self.pk).update(
                is_default=False
            )

