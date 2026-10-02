from django.contrib import admin

from .models import Category, Product, ProductImage, ProductVolume, Review, Volume


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "image_preview")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")

    @admin.display(description="Image")
    def image_preview(self, obj):
        return "Yes" if obj.image else "No"


@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ("ml", "cost", "price")
    ordering = ("ml",)
    search_fields = ("ml",)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "is_default", "is_active", "sort_order")


class ProductVolumeInline(admin.TabularInline):
    model = ProductVolume
    extra = 1
    fields = (
        "volume",
        "product_type",
        "price",
        "unit_cost",
        "stock_quantity",
        "sku",
        "barcode",
        "variant_image",
        "is_active",
    )
    readonly_fields = ()
    show_change_link = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "gender",
        "status",
        "is_featured",
        "base_price",
        "is_in_stock",
        "created_at",
    )
    list_filter = ("status", "is_featured", "gender", "category")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = (
        "uuid",
        "base_price",
        "gross_profit_amount",
        "gross_margin_percent",
        "average_rating",
        "total_reviews",
    )
    search_fields = ("name", "slug", "category__name", "supplier__name")
    inlines = (ProductVolumeInline, ProductImageInline)


@admin.register(ProductVolume)
class ProductVolumeAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "variant_label",
        "sku",
        "effective_price",
        "effective_cost",
        "discount_value",
        "stock_quantity",
        "is_active",
        "sort_order",
    )
    list_filter = ("is_active", "product_type", "volume", "color", "size", "scent")
    search_fields = ("product__name", "name", "sku", "barcode", "color", "size", "scent")
    readonly_fields = (
        "variant_label",
        "effective_price",
        "effective_cost",
        "gross_profit_amount",
        "gross_margin_percent",
        "is_in_stock",
    )
    fieldsets = (
        (
            "Variant",
            {
                "fields": (
                    "product",
                    "volume",
                    "product_type",
                    "price",
                    "unit_cost",
                    "stock_quantity",
                    "sku",
                    "barcode",
                    "variant_image",
                    "is_active",
                )
            },
        ),
        (
            "Advanced",
            {
                "classes": ("collapse",),
                "fields": (
                    "name",
                    "discount_value",
                    "color",
                    "size",
                    "scent",
                    "attributes",
                    "max_quantity_per_order",
                    "sort_order",
                ),
            },
        ),
        (
            "Read-only metrics",
            {
                "fields": (
                    "variant_label",
                    "effective_price",
                    "effective_cost",
                    "gross_profit_amount",
                    "gross_margin_percent",
                    "is_in_stock",
                )
            },
        ),
    )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "alt_text", "is_default", "is_active", "sort_order")
    list_filter = ("is_default", "is_active")
    search_fields = ("product__name", "alt_text")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "is_verified", "created_at")
    list_filter = ("rating", "is_verified", "created_at")
    search_fields = ("product__name", "user__username", "review_text")
