from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from .validators import build_youtube_embed_url, validate_youtube_url


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]
        indexes = [models.Index(fields=["slug"], name="blog_category_slug_idx")]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Comment(models.Model):
    post = models.ForeignKey(
        "BlogPost", on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Comment"
        verbose_name_plural = "Comments"
        indexes = [
            models.Index(fields=["post", "created_at"], name="blog_comment_post_created_idx"),
            models.Index(fields=["author", "created_at"], name="blg_cmt_auth_cr_idx"),
        ]

    def __str__(self):
        return f"Comment by {self.author} on '{self.post.title}'"


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["name"]
        indexes = [models.Index(fields=["slug"], name="blog_tag_slug_idx")]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    content = models.TextField()  # Text content (rich or plain)
    url_content = models.URLField(
        blank=True, null=True, validators=[validate_youtube_url]
    )  # YouTube or other URLs

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="posts"
    )
    tags = models.ManyToManyField(
        Tag, blank=True, related_name="posts"
    )  # Many-to-many relationship with Tag
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Blog Post"
        verbose_name_plural = "Blog Posts"
        indexes = [
            models.Index(fields=["slug"], name="blog_post_slug_idx"),
            models.Index(fields=["is_published", "created_at"], name="blg_post_pub_cr_idx"),
            models.Index(fields=["category", "is_published"], name="blog_post_category_pub_idx"),
            models.Index(fields=["author", "created_at"], name="blog_post_author_created_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def youtube_embed_url(self):
        return build_youtube_embed_url(self.url_content or "")
