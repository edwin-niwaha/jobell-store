from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("get_full_name", "email", "mobile", "tel", "created_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("first_name", "last_name", "email", "mobile", "tel", "address")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
