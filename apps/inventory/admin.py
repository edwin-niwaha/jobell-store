from django.contrib import admin

from .models import Inventory


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "low_stock_threshold", "is_out_of_stock", "low_stock", "updated_at")
    list_filter = ("is_out_of_stock", "updated_at")
    search_fields = ("product__name", "product__category__name")
    raw_id_fields = ("product",)
    readonly_fields = ("created_at", "updated_at")
