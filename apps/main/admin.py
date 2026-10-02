from django.contrib import admin

from .models import Subscriber, Testimonial


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("author", "approved", "created_at")
    list_filter = ("approved", "created_at")
    search_fields = ("author", "text")
    readonly_fields = ("created_at",)


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "consent", "created_at", "updated_at")
    list_filter = ("consent", "created_at")
    search_fields = ("email",)
    readonly_fields = ("created_at", "updated_at")
