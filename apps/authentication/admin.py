from django.contrib import admin

from .models import Contact, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "branch", "mobile", "tel")
    list_filter = ("role", "branch")
    search_fields = ("user__username", "user__email", "mobile", "tel")
    raw_id_fields = ("user", "branch")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "is_valid", "created_at")
    list_filter = ("is_valid", "created_at")
    search_fields = ("name", "email", "message")
    readonly_fields = ("created_at",)
