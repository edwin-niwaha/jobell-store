from django.contrib import admin

from .models import DeliveryRate, PickupStation


@admin.register(PickupStation)
class PickupStationAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "area", "phone", "is_active")
    list_filter = ("city", "area", "is_active")
    search_fields = ("name", "city", "area", "address", "phone")


@admin.register(DeliveryRate)
class DeliveryRateAdmin(admin.ModelAdmin):
    list_display = (
        "region",
        "city",
        "area",
        "fee",
        "estimated_days",
        "is_active",
    )
    list_filter = ("region", "city", "is_active")
    search_fields = ("city", "area")

