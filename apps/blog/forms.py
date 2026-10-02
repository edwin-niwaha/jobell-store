from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import BlogPost, Category, Tag, Comment
from .validators import validate_youtube_url


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter category name"}
            ),
        }
        labels = {
            "name": "Category Name",
        }


class BlogPostForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5, "cols": 40}),
        label="Content",
    )

    url_content = forms.URLField(
        required=False,
        validators=[validate_youtube_url],
        label="YouTube Video URL",
        widget=forms.URLInput(attrs={"class": "form-control"}),
    )

    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        required=True,
        label="Tags",
    )

    class Meta:
        model = BlogPost
        fields = [
            "title",
            "content",
            "url_content",
            "category",
            "tags",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter blog post title"}
            ),
            "category": forms.Select(attrs={"class": "form-control"}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_title(self):
        """Ensure the title is at least 5 characters long."""
        title = self.cleaned_data.get("title")
        if len(title) < 5:
            raise ValidationError("The title must be at least 5 characters long.")
        return title

    def clean_url_content(self):
        """Validate the YouTube URL in the `url_content` field."""
        url_content = self.cleaned_data.get("url_content")
        if url_content:
            try:
                validate_youtube_url(url_content)
            except ValidationError:
                raise ValidationError(
                    "Invalid YouTube URL. Please ensure it is correct."
                )
        return url_content

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        tags = cleaned_data.get("tags")

        if not category:
            raise ValidationError("You must select a category for the blog post.")

        if not tags:
            raise ValidationError("At least one tag must be selected.")

        return cleaned_data


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name"]  # Only allow name input for tag creation

        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter tag name"}
            )
        }

    def clean_name(self):
        """Ensure that the tag name is not too short."""
        name = self.cleaned_data.get("name", "").strip()
        if len(name) < 3:
            raise forms.ValidationError(
                "The tag name must be at least 3 characters long."
            )
        if Tag.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("A tag with this name already exists.")
        if Tag.objects.filter(slug=slugify(name)).exists():
            raise forms.ValidationError("A tag with a similar URL slug already exists.")
        return name


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Write your comment...",
                    "rows": 3,
                }
            ),
        }
