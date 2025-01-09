import json
from django.http import JsonResponse
from datetime import date, timedelta
from django.db.models.functions import ExtractYear
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, FloatField, F
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.db.models import Min, Max
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from apps.products.models import Product, Category
from .forms import ProductFilterForm
from apps.sales.models import Sale
from apps.orders.models import Cart, CartItem, Order, Wishlist

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
    products = Product.objects.prefetch_related("images", "productvolume_set").filter(
        status="ACTIVE"
    ).order_by("name")

    # Initialize counts for cart, wishlist, and orders
    cart_count = 0
    wishlist_count = 0
    order_count = 0

    # Fetch the user's cart and calculate the cart count only if the user is authenticated
    if request.user.is_authenticated:
        # Ensure the user is a Customer instance (if needed)
        customer = None
        if hasattr(request.user, "customer"):
            customer = (
                request.user.customer
            )  # Assuming a one-to-one relationship between User and Customer

        # Get or create the user's cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        cart_count = sum(item.quantity for item in cart_items)

        # Fetch the user's wishlist count
        wishlist_count = Wishlist.objects.filter(user=request.user).count()

        # Fetch the user's order count
        # If Order model expects a Customer instance, ensure we're using the Customer instance
        if customer:
            order_count = Order.objects.filter(customer=customer).count()
        else:
            order_count = 0  # If there's no customer instance, handle accordingly

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
                productvolume__price__gte=min_price, productvolume__price__lte=max_price
            )
        elif min_price is not None:
            products = products.filter(productvolume__price__gte=min_price)
        elif max_price is not None:
            products = products.filter(productvolume__price__lte=max_price)

        # Filter by search query if provided
        if search_query:
            products = products.filter(name__icontains=search_query)

    # Pagination setup
    paginator = Paginator(products, 12)  # Show 12 products per page
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
            min_vol_price = volumes.aggregate(Min("price"))["price__min"]
            max_vol_price = volumes.aggregate(Max("price"))["price__max"]
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
