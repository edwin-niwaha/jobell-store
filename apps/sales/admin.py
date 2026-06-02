from django.contrib import admin

from .models import Sale, SaleDetail


class SaleDetailInline(admin.TabularInline):
    model = SaleDetail
    extra = 0
    raw_id_fields = ("product", "product_volume")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "receipt_number", "customer", "sale_type", "payment_method", "grand_total", "trans_date")
    list_filter = ("sale_type", "payment_method", "trans_date")
    search_fields = ("receipt_number", "customer__first_name", "customer__last_name", "order__id")
    raw_id_fields = ("order", "customer")
    date_hierarchy = "trans_date"
    inlines = (SaleDetailInline,)


@admin.register(SaleDetail)
class SaleDetailAdmin(admin.ModelAdmin):
    list_display = ("sale", "product", "product_volume", "quantity", "price", "total_detail")
    search_fields = ("sale__receipt_number", "product__name", "product_volume__sku")
    raw_id_fields = ("sale", "product", "product_volume")
