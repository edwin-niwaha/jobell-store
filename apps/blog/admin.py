from django.contrib import admin

from .models import BlogPost, Category, Comment, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ("author", "content", "created_at")
    readonly_fields = ("created_at",)
    raw_id_fields = ("author",)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "is_published", "created_at", "updated_at")
    list_filter = ("is_published", "category", "created_at")
    search_fields = ("title", "content", "category__name", "tags__name", "author__username")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author", "category")
    filter_horizontal = ("tags",)
    date_hierarchy = "created_at"
    inlines = (CommentInline,)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("post__title", "author__username", "content")
    raw_id_fields = ("post", "author")
