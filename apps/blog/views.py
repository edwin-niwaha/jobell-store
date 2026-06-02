import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required


from .models import BlogPost, Category
from .forms import BlogPostForm, CategoryForm, TagForm, CommentForm
from apps.authentication.decorators import (
    admin_required,
    admin_or_manager_or_staff_required,
)

logger = logging.getLogger(__name__)


# =================================== Blog List View ===================================
def blog_list(request):
    # Fetch only published posts
    # posts = BlogPost.objects.filter(is_published=True).order_by('-created_at')
    posts = BlogPost.objects.order_by("-created_at")
    # Paginate the posts
    paginator = Paginator(posts, 5)  # 5 posts per page
    page_number = request.GET.get(
        "page", 1
    )  # Default to page 1 if no page is specified

    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Render the blog list template
    return render(request, "blog/blog_list.html", {"page_obj": page_obj})


# =================================== Category Add View ===================================
@login_required
@admin_or_manager_or_staff_required
def blog_category_add(request):
    """Create a new category with validation."""
    form_title = "Add New Category"

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category_name = form.cleaned_data["name"]
            if Category.objects.filter(name=category_name).exists():
                messages.error(
                    request,
                    f"A category with the name '{category_name}' already exists.",
                    extra_tags="warning",
                )
            else:
                try:
                    form.save()
                    messages.success(
                        request,
                        f"Category '{category_name}' created successfully!",
                        extra_tags="bg-success",
                    )
                    return redirect("blog:blog_category_add")
                except Exception:
                    logger.exception("Error creating blog category %s", category_name)
                    messages.error(
                        request,
                        "An error occurred during category creation.",
                        extra_tags="bg-danger",
                    )
                    return redirect("blog:blog_category_add")
        else:
            messages.error(
                request,
                "Please correct the errors below.",
                extra_tags="warning",
            )
    else:
        form = CategoryForm()

    return render(
        request,
        "blog/category_add.html",
        {
            "form": form,
            "form_title": form_title,
        },
    )


# =================================== Blog Create View ===================================
@login_required
@admin_or_manager_or_staff_required
def blog_create(request):
    """Create a new blog post."""
    form_title = "Create Blog Post"

    if request.method == "POST":
        form = BlogPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user  # Set the current user as the author
            post.save()
            form.save_m2m()  # Save many-to-many relationships (tags)

            # Add a success message
            messages.success(
                request, "Blog post created successfully!", extra_tags="bg-success"
            )

            # Redirect to the blog post's detail page (or any other view)
            return redirect("blog:blog_list")
        else:
            # Add an error message if the form is not valid
            messages.error(
                request,
                "There were errors in your form. Please try again.",
                extra_tags="bg-danger",
            )

    else:
        form = BlogPostForm()  # Create an empty form on GET request

    return render(
        request,
        "blog/blog_form.html",
        {
            "form": form,
            "form_title": form_title,
        },
    )


# =================================== Tag Add View ===================================
@login_required
@admin_or_manager_or_staff_required
def add_tag(request):
    """View to handle creating a new tag."""
    form = TagForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(
                request, "Tag created successfully!", extra_tags="bg-success"
            )
            return redirect(
                "blog:add_tag"
            )  # Redirect back to the form or another page after success
        else:
            messages.error(
                request,
                "There was an error with the form. Please correct the errors below.",
            )

    return render(request, "blog/add_tag.html", {"form": form})


# =================================== Blog Edit View ===================================
@login_required
@admin_required
@transaction.atomic
def blog_edit(request, id):
    # Fetch the blog post using the provided id (primary key)
    post = get_object_or_404(BlogPost, id=id)

    # Handle form submission (POST)
    if request.method == "POST":
        form = BlogPostForm(request.POST, instance=post)
        if form.is_valid():
            # Save the updated form data
            form.save()
            messages.success(
                request, "Blog post updated successfully!", extra_tags="bg-success"
            )
            return redirect(
                "blog:blog_list"
            )  # Redirect to the blog list page after successful update

    # Handle GET request (show existing form)
    else:
        form = BlogPostForm(instance=post)

    # Render the form in the template
    return render(request, "blog/blog_form.html", {"form": form})


# =================================== Blog Delete View ===================================
@login_required
@admin_required
@transaction.atomic
def blog_delete(request, id):  # Use id instead of slug
    post = get_object_or_404(BlogPost, id=id)  # Fetch the post using id (primary key)

    if request.method == "POST":
        post.delete()
        messages.success(
            request, "Blog post deleted successfully!", extra_tags="bg-danger"
        )
        return redirect("blog:blog_list")  # Redirect to the blog list after deletion

    return render(request, "blog/blog_list.html")


# =================================== Blog Comment View ===================================
@login_required
def post_comment(request, post_id):
    # Retrieve the blog post
    post = get_object_or_404(BlogPost, id=post_id)

    if request.method == "POST":
        # Instantiate the form with POST data
        form = CommentForm(request.POST)
        if form.is_valid():
            # Save the comment but don't commit yet
            comment = form.save(commit=False)
            comment.post = post  # Associate comment with the post
            comment.author = (
                request.user
            )  # Associate the comment with the logged-in user
            comment.save()  # Save the comment to the database

            # Add a success message
            messages.success(
                request,
                "Your comment has been posted successfully.",
                extra_tags="bg-success",
            )

            # Redirect to the blog detail page after successfully posting the comment
            return redirect("blog:blog_detail", post_id=post.id)
    else:
        # Empty form for GET request
        form = CommentForm()

    # Render the blog detail template with the comment form
    return render(request, "blog/blog_detail.html", {"post": post, "form": form})


# =================================== Comment Detail View ===================================
@login_required
def blog_detail(request, post_id):
    # Retrieve the blog post
    post = get_object_or_404(BlogPost, id=post_id)

    # Get all the comments related to the post
    comments = post.comments.all()

    # Instantiate the comment form
    form = CommentForm()

    # Render the blog detail template with post, comments, and form
    return render(
        request,
        "blog/blog_detail.html",
        {"post": post, "comments": comments, "form": form},
    )
