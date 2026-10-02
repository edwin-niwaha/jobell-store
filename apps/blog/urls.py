from django.urls import path
from . import views

app_name = "blog"

urlpatterns = [
    # Blog List and Details
    path("", views.blog_list, name="blog_list"),
    path("post/<int:post_id>/comment/", views.post_comment, name="post_comment"),
    path("post/<int:post_id>/", views.blog_detail, name="blog_detail"),
    # Blog Post Management
    path("create/", views.blog_create, name="blog_create"),
    path("edit/<int:id>/", views.blog_edit, name="blog_edit"),
    path("delete/<int:id>/", views.blog_delete, name="blog_delete"),
    # Blog Categories
    path("category/add/", views.blog_category_add, name="blog_category_add"),
    # Blog Tags
    path("tag/add/", views.add_tag, name="add_tag"),
]
