from django.contrib import admin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_name", "email", "phone", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "contact_name", "email", "phone", "address")
    readonly_fields = ("created_at",)
