from django.contrib import admin

from .models import CustomerAddress


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "city",
        "area",
        "region",
        "phone_number",
        "is_default",
        "updated_at",
    )
    list_filter = ("region", "city", "is_default", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "street_name",
        "city",
        "area",
        "phone_number",
    )
    autocomplete_fields = ("user",)

