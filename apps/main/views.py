import json
from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from decimal import Decimal
from datetime import date, timedelta
from django.db.models.functions import ExtractYear
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, FloatField, F
from django.db.models.functions import Coalesce
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Min, Max
from django.core.paginator import Paginator, EmptyPage

from apps.products.models import Product, Category, Review
from apps.sales.models import Sale
from apps.orders.models import Cart, CartItem, Order, Wishlist

from .models import Testimonial, Subscriber
from .forms import TestimonialForm, NewsletterForm, EmailForm
from apps.products.forms import ProductFilterForm

from apps.authentication.decorators import (
    admin_or_manager_or_staff_required,
)

from .utils import (
    get_top_selling_products,
)


# =================================== Home User view  ===================================
def index(request):
    # Initialize the filter form
    form = ProductFilterForm(request.GET)

    # Start with all active products
    products = (
        Product.objects.prefetch_related("images", "productvolume_set")
        .filter(status="ACTIVE", is_featured=True)
        .order_by("name")
    )

    # Initialize counts for cart, wishlist, and orders
    cart_count = 0
    wishlist_count = 0
    order_count = 0

    # Fetch the user's cart and calculate the cart count only if the user is authenticated
    if request.user.is_authenticated:
        customer = getattr(request.user, "customer", None)

        # Get or create the user's cart
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_count = (
            CartItem.objects.filter(cart=cart).aggregate(
                total_quantity=Sum("quantity")
            )["total_quantity"]
            or 0
        )

        # Fetch the user's wishlist count
        wishlist_count = Wishlist.objects.filter(user=request.user).count()

        # Fetch the user's order count, ensuring a valid customer instance
        order_count = Order.objects.filter(customer=customer).count() if customer else 0

    # Apply filters if the form is valid
    if form.is_valid():
        category_filter = form.cleaned_data.get("category")
        min_price = form.cleaned_data.get("min_price")
        max_price = form.cleaned_data.get("max_price")
        search_query = form.cleaned_data.get("search")

        # Filter by category if selected
        if category_filter:
            products = products.filter(category=category_filter)

        # Filter by price range if provided
        if min_price is not None and max_price is not None:
            products = products.filter(
                productvolume__volume__price__gte=min_price,
                productvolume__volume__price__lte=max_price,
            ).distinct()
        elif min_price is not None:
            products = products.filter(
                productvolume__volume__price__gte=min_price
            ).distinct()
        elif max_price is not None:
            products = products.filter(
                productvolume__volume__price__lte=max_price
            ).distinct()

        # Filter by search query if provided
        if search_query:
            products = products.filter(name__icontains=search_query)

    # Pagination setup
    paginator = Paginator(products, 16)
    page_number = request.GET.get("page", 1)

    try:
        page_number = int(page_number)
        if page_number < 1:
            page_number = 1
    except ValueError:
        page_number = 1

    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Prepare the products with images and volumes
    products_with_images = []
    for product in page_obj:
        images = product.images.filter(is_default=True)
        if not images.exists():
            images = product.images.all()

        volumes = product.productvolume_set.all()
        if volumes.exists():
            min_vol_price = volumes.aggregate(Min("volume__price"))[
                "volume__price__min"
            ]
            max_vol_price = volumes.aggregate(Max("volume__price"))[
                "volume__price__max"
            ]
        else:
            min_vol_price = max_vol_price = None

        products_with_images.append(
            {
                "product": product,
                "images": images,
                "min_price": min_vol_price,
                "max_price": max_vol_price,
            }
        )

    # Handle testimonial and nesletter forms submission
    testimonial_form = TestimonialForm(request.POST or None)
    newsletter_form = NewsletterForm(request.POST or None)

    if request.method == "POST" and testimonial_form.is_valid():
        testimonial_form.save()
        messages.success(
            request,
            "Your testimonial has been submitted successfully!",
            extra_tags="bg-success",
        )
        return redirect("users-home")

    # Handle Newsletter Form Submission
    if "submit_newsletter" in request.POST and newsletter_form.is_valid():
        newsletter_form.save()
        messages.success(
            request,
            "Thank you for subscribing to our newsletter!",
            extra_tags="bg-success",
        )
        return redirect("users-home")

    # Fetch all testimonials to display in the template
    testimonials = Testimonial.objects.filter(approved=True)

    # Pass the form, filtered products, and pagination to the template
    return render(
        request,
        "index.html",
        {
            "form": form,
            "products_with_images": products_with_images,
            "user": request.user,
            "page_obj": page_obj,
            "cart_count": cart_count,
            "wishlist_count": wishlist_count,
            "order_count": order_count,
            "testimonial_form": testimonial_form,
            "testimonials": testimonials,
            "newsletter_form": newsletter_form,
        },
    )


@login_required
@admin_or_manager_or_staff_required
def get_total_sales_for_period(start_date, end_date):
    return (
        Sale.objects.filter(trans_date__range=[start_date, end_date]).aggregate(
            total_sales=Sum("grand_total")
        )["total_sales"]
        or 0
    )


# =================================== The dashboard view ===================================from django.db.models import Sum


@login_required
@admin_or_manager_or_staff_required
def dashboard(request):
    today = date.today()
    year = today.year

    # Helper function to get total sales for a period
    def get_total_sales_for_period(start_date, end_date):
        return (
            Sale.objects.filter(trans_date__range=[start_date, end_date]).aggregate(
                total_sales=Coalesce(Sum("grand_total"), 0.0)
            )["total_sales"]
            or 0
        )

    # Calculate monthly and annual earnings
    monthly_earnings = [
        Sale.objects.filter(trans_date__year=year, trans_date__month=month).aggregate(
            total=Coalesce(Sum("grand_total"), 0.0)
        )["total"]
        for month in range(1, 13)
    ]
    annual_earnings = format(sum(monthly_earnings), ".2f")
    avg_month = format(sum(monthly_earnings) / 12, ".2f")

    # Get total sales for today, week, and month
    total_sales_today = get_total_sales_for_period(today, today)
    total_sales_week = get_total_sales_for_period(
        today - timedelta(days=today.weekday()), today
    )
    total_sales_month = get_total_sales_for_period(today.replace(day=1), today)

    # Get top-selling products using the new method
    top_products = get_top_selling_products()

    # Fetch all sales and prefetch related data
    sales = Sale.objects.prefetch_related(
        "items__product_volume__volume", "items__product"
    )

    # Initialize total profit after sales
    total_profit_after_sales = Decimal(0)

    # Calculate total profit from all sales
    for sale in sales:
        for item in sale.items.all():
            product = item.product
            product_volume = item.product_volume

            # Determine volume and price details
            volume = product_volume.volume if product_volume else None
            cost = volume.cost if volume else 0
            discounted_price = item.price  # Price directly from SaleDetail

            # Calculate and accumulate profit
            item_profit = (Decimal(discounted_price) - Decimal(cost)) * Decimal(
                item.quantity
            )
            total_profit_after_sales += item_profit

    # total_profit_after_sales now holds the total profit from all sales

    # Total stock from Inventory
    total_stock = Product.objects.filter(status="ACTIVE").aggregate(
        total=Coalesce(Sum("inventory__quantity"), 0)
    )["total"]

    context = {
        "products": Product.objects.filter(status="ACTIVE").count(),
        "total_stock": total_stock,
        "categories": Category.objects.count(),
        "annual_earnings": annual_earnings,
        "monthly_earnings": json.dumps(monthly_earnings),
        "avg_month": avg_month,
        "total_sales_today": total_sales_today,
        "total_sales_week": total_sales_week,
        "total_sales_month": total_sales_month,
        "top_products": top_products,
        "total_profit_after_sales": total_profit_after_sales,
    }

    return render(request, "main/dashboard.html", context)


@login_required
@admin_or_manager_or_staff_required
def monthly_earnings_view(request):
    today = date.today()
    year = today.year
    monthly_earnings = []

    for month in range(1, 13):
        earning = (
            Sale.objects.filter(trans_date__year=year, trans_date__month=month)
            .aggregate(
                total_variable=Coalesce(
                    Sum(F("grand_total")), 0.0, output_field=FloatField()
                )
            )
            .get("total_variable")
        )
        monthly_earnings.append(earning)

    return JsonResponse(
        {
            "labels": [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ],
            "data": monthly_earnings,
        }
    )


# =================================== Annual Sales graph ===================================
@login_required
@admin_or_manager_or_staff_required
def sales_data_api(request):
    # Query to get total sales grouped by year
    sales_per_year = (
        Sale.objects.annotate(year=ExtractYear("trans_date"))
        .values("year")
        .annotate(total_sales=Sum("grand_total"))
        .order_by("year")
    )

    # Prepare the data as a dictionary
    data = {
        "years": [item["year"] for item in sales_per_year],
        "total_sales": [item["total_sales"] for item in sales_per_year],
    }

    # Return the data as JSON
    return JsonResponse(data)


# =================================== testimonials_view ===================================


def testimonials_view(request):
    # Fetch all testimonials
    testimonials_list = Testimonial.objects.all()

    # Pagination setup
    paginator = Paginator(testimonials_list, 20)  # Show 20 testimonials per page
    page_number = request.GET.get("page")
    testimonials = paginator.get_page(page_number)

    if request.method == "POST":
        # Handle approval or rejection of a testimonial
        testimonial_id = request.POST.get("testimonial_id")
        action = request.POST.get("action")

        if testimonial_id:
            testimonial = Testimonial.objects.get(id=testimonial_id)
            if action == "approve":
                testimonial.approved = True
            elif action == "reject":
                testimonial.approved = False
            elif action == "delete":
                testimonial.delete()
            testimonial.save()

        return redirect("testimonials")  # Redirect to the same page after action

    table_title = "Testimonials Management"
    return render(
        request,
        "main/testimonials.html",
        {"testimonials": testimonials, "table_title": table_title},
    )


# =================================== update_testimonial ===================================
@login_required
@admin_or_manager_or_staff_required
def testimonial_update(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk)

    if request.method == "POST":
        form = TestimonialForm(request.POST, instance=testimonial)
        if form.is_valid():
            form.save()
            return redirect("testimonials")  # Redirect to the testimonials list page
    else:
        form = TestimonialForm(instance=testimonial)

        # Add 'form_title' to the context
    context = {
        "form": form,
        "testimonial": testimonial,
        "form_title": "Update Testimonial",  # Title for the form
    }

    return render(request, "main/testimonial_update.html", context)


# =================================== delete_testimonial ===================================
@login_required
@admin_or_manager_or_staff_required
def testimonial_delete(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk)

    try:
        testimonial.delete()
        messages.success(
            request, "Testimonial deleted successfully.", extra_tags="bg-danger"
        )
    except Exception as e:
        messages.error(
            request, "There was an error during the deletion!", extra_tags="bg-danger"
        )
        print(e)

    return redirect("testimonials")


# =================================== Subscribers List ===================================
@login_required
@admin_or_manager_or_staff_required
def subscriber_list_view(request):
    subscriber_list = Subscriber.objects.all().order_by("id")

    # Pagination logic
    paginator = Paginator(subscriber_list, 50)
    page_number = request.GET.get("page")
    subscribers = paginator.get_page(page_number)

    context = {
        "subscribers": subscribers,
        "table_title": "Subscribers List",
    }
    return render(request, "main/subscriber.html", context)


# =================================== delete subscribers ===================================


@login_required
@admin_or_manager_or_staff_required
def delete_subscriber_view(request, subscriber_id):
    subscriber = get_object_or_404(Subscriber, id=subscriber_id)
    subscriber.delete()
    messages.success(
        request, "Subscriber deleted successfully.", extra_tags="bg-danger"
    )
    return redirect("subscriber_list")


# =================================== Send Email ===================================
def send_bulk_email_view(request):
    table_title = "Subscriber Email List"

    if request.method == "POST":
        form = EmailForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data["subject"]
            message = form.cleaned_data["message"]  # This will be rich text
            from_email = settings.EMAIL_HOST_USER

            # Fetch all subscriber emails
            recipients = list(Subscriber.objects.values_list("email", flat=True))

            if recipients:
                send_mail(
                    subject,
                    message,
                    from_email,
                    recipients,
                    fail_silently=False,
                    html_message=message,  # Send the message as HTML content
                )
                messages.success(
                    request,
                    "Email sent successfully to all subscribers.",
                    extra_tags="bg-success",
                )
            else:
                messages.warning(request, "No subscribers to send email to.")
            return redirect("send_bulk_email")  # Prevent resubmission

    else:
        form = EmailForm()

    subscribers = Subscriber.objects.all().order_by("id")
    paginator = Paginator(subscribers, 10)
    page_number = request.GET.get("page")
    subscribers = paginator.get_page(page_number)

    context = {
        "form": form,
        "table_title": table_title,
        "subscribers": subscribers,
    }

    return render(request, "main/send_bulk_email.html", context)


# =================================== Reviews ===================================
def reviews_list_view(request):
    reviews = Review.objects.all()  # Fetch all reviews
    if request.method == "POST":
        review_id = request.POST.get("review_id")
        action = request.POST.get("action")
        review = get_object_or_404(Review, id=review_id)

        if action == "verify" and not review.is_verified:
            review.is_verified = True
            review.save()
            messages.success(
                request,
                f"Review for {review.product.name} has been verified.",
                extra_tags="bg-success",
            )

        return redirect("reviews_list")  # Redirect to the reviews list page

    return render(request, "main/reviews_list.html", {"reviews": reviews})


def toggle_is_verified(request, review_id):
    # Fetch the review object based on the given ID
    review = get_object_or_404(Review, id=review_id)

    # Toggle the 'is_verified' status if it's not already verified
    if not review.is_verified:
        review.is_verified = True
        review.save()

    # Return a JSON response with the updated status
    return JsonResponse({"is_verified": review.is_verified})


def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, "Review deleted successfully.", extra_tags="bg-danger")
    return redirect("reviews_list")
