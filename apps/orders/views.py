from django.core.mail import EmailMultiAlternatives
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Sum
from django.conf import settings
from django.contrib import messages
from decimal import Decimal
import requests
import uuid
from django.http import JsonResponse
import logging
import base64
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.db import transaction
from .models import Cart, CartItem, Order, OrderDetail, Wishlist
from .services import cart_total, create_order_from_cart, get_or_create_cart
from apps.products.models import Product, ProductVolume, ProductImage
from apps.products.selectors import build_storefront_product_card

# from django.core.exceptions import MultipleObjectsReturned
from .forms import CheckoutForm, OrderStatusForm
from apps.customers.models import Customer
from apps.products.models import Review
from apps.addresses.models import CustomerAddress
from apps.shipping.services import delivery_quote_for

from apps.authentication.decorators import (
    admin_required,
    admin_or_manager_or_staff_required,
)


logger = logging.getLogger(__name__)


def _safe_redirect_target(request, fallback):
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(
        target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return target
    return fallback


def _wants_json(request):
    return (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or "application/json" in request.headers.get("accept", "")
    )


def _cart_count(cart):
    return (
        cart.items.aggregate(total_quantity=Sum("quantity"))["total_quantity"]
        or 0
    )


def _cart_json_response(cart, message="Product added to cart successfully.", status=200):
    return JsonResponse(
        {
            "ok": status < 400,
            "message": message,
            "cart_count": _cart_count(cart),
            "cart_url": reverse("orders:cart"),
        },
        status=status,
    )


def _user_has_bought_product(user, product):
    if not user.is_authenticated:
        return False
    return (
        OrderDetail.objects.filter(order__customer__user=user, product=product)
        .exclude(order__status__in=["Canceled", "Refunded", "Returned"])
        .exists()
    )


# =================================== Products Detail ===================================


# @login_required
# def product_detail(request, product_uuid):
#     product = get_object_or_404(Product.objects.select_related("category", "supplier").prefetch_related("images", "productvolume_set__volume"), uuid=product_uuid)

#     # Handle review submission
#     if request.method == "POST" and "submit_review" in request.POST:
#         if Review.objects.filter(product=product, user=request.user).exists():
#             # Add message for already reviewed
#             messages.info(
#                 request,
#                 "Oops! You've already reviewed this product.",
#                 extra_tags="bg-danger",
#             )
#             return redirect("orders:product_detail", product_uuid=product_uuid)

#         review_text = request.POST.get("review_text")
#         rating = int(request.POST.get("rating"))

#         if review_text and rating:
#             Review.objects.create(
#                 product=product,
#                 user=request.user,
#                 review_text=review_text,
#                 rating=rating,
#             )

#         # Redirect to prevent re-posting the form if refreshed
#         return redirect("orders:product_detail", product_uuid=product_uuid)

#     # Handle "Set as Featured" or "Remove from Featured" based on the POST request
#     if request.method == "POST":
#         # Check if we are toggling 'is_featured'
#         if "set_featured" in request.POST:
#             product.is_featured = True
#         elif "remove_featured" in request.POST:
#             product.is_featured = False

#         # Save the updated product
#         product.save()
#         return redirect("orders:product_detail", product_uuid=product_uuid)

#     # Continue fetching cart and product details
#     cart, created = Cart.objects.get_or_create(user=request.user)
#     cart_items = CartItem.objects.filter(cart=cart).select_related("product", "volume", "volume__volume")
#     cart_count = sum(item.quantity for item in cart_items)

#     # Fetch volumes specific to this product
#     product_volumes = ProductVolume.objects.filter(product=product).order_by(
#         "volume__ml"
#     )

#     # Fetch reviews
#     reviews = Review.objects.filter(product=product, is_verified=True).order_by(
#         "-created_at"
#     )

#     # Pagination
#     paginator = Paginator(reviews, 5)  # Show 5 reviews per page
#     page_number = request.GET.get("page")
#     page_obj = paginator.get_page(page_number)

#     # Count of verified reviews (assuming there is an 'is_verified' field in your Review model)
#     verified_reviews_count = reviews.filter(is_verified=True).count()

#     # Process reviews to generate the filled and empty stars
#     for review in page_obj:
#         review.filled_stars = "★" * review.rating
#         review.empty_stars = "☆" * (5 - review.rating)

#     context = {
#         "product": product,
#         "product_volumes": product_volumes,
#         "cart_count": cart_count,
#         "reviews": page_obj,  # Pass paginated reviews
#         "verified_reviews_count": verified_reviews_count,  # Add verified reviews count
#     }

#     return render(request, "orders/product_detail.html", context)


def product_detail(request, product_uuid):
    product = get_object_or_404(
        Product.objects.select_related("category", "supplier").prefetch_related("images"),
        uuid=product_uuid,
    )
    has_bought_product = _user_has_bought_product(request.user, product)
    user_review_exists = (
        request.user.is_authenticated
        and Review.objects.filter(product=product, user=request.user).exists()
    )
    can_review = has_bought_product and not user_review_exists

    # Handle review submission
    if request.method == "POST" and "submit_review" in request.POST:
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to submit a review.")
            return redirect("orders:product_detail", product_uuid=product_uuid)
        if not has_bought_product:
            messages.error(
                request,
                "Only customers who bought this product can leave a review.",
                extra_tags="bg-danger text-white",
            )
            return redirect("orders:product_detail", product_uuid=product_uuid)
        if Review.objects.filter(product=product, user=request.user).exists():
            messages.info(
                request, "You've already reviewed this product.", extra_tags="bg-danger"
            )
            return redirect("orders:product_detail", product_uuid=product_uuid)
        review_text = request.POST.get("review_text")
        rating = int(request.POST.get("rating", 0))
        if review_text and 1 <= rating <= 5:
            Review.objects.create(
                product=product,
                user=request.user,
                review_text=review_text,
                rating=rating,
                is_verified=True,
            )
            messages.success(
                request,
                "Review submitted successfully.",
                extra_tags="bg-success text-white",
            )
        else:
            messages.error(
                request, "Invalid review data.", extra_tags="bg-danger text-white"
            )
        return redirect("orders:product_detail", product_uuid=product_uuid)

    # Handle featured toggle
    if request.method == "POST" and (
        "set_featured" in request.POST or "remove_featured" in request.POST
    ):
        if request.user.has_perm("orders.change_product"):
            product.is_featured = "set_featured" in request.POST
            product.save()
            messages.success(
                request,
                f"Product {'featured' if product.is_featured else 'unfeatured'}.",
                extra_tags="bg-success text-white",
            )
        else:
            messages.error(
                request, "Permission denied.", extra_tags="bg-danger text-white"
            )
        return redirect("orders:product_detail", product_uuid=product_uuid)

    cart = get_or_create_cart(request)

    cart_items = CartItem.objects.filter(cart=cart).select_related("product", "volume", "volume__volume")
    cart_count = sum(item.quantity for item in cart_items)

    # Fetch product volumes
    product_volumes = ProductVolume.objects.filter(
        product=product, is_active=True
    ).filter(
        Q(stock_quantity__isnull=True) | Q(stock_quantity__gt=0)
    ).order_by(
        "sort_order", "volume__ml", "product_type"
    )

    # Fetch and paginate reviews
    reviews = Review.objects.filter(product=product, is_verified=True).order_by(
        "-created_at"
    )
    average_rating = reviews.aggregate(value=Avg("rating"))["value"]
    paginator = Paginator(reviews, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    for review in page_obj:
        review.filled_stars = range(review.rating)
        review.empty_stars = range(5 - review.rating)

    product_images = product.image_urls
    if not product_images:
        product_images = []

    review_block_reason = ""
    if not request.user.is_authenticated:
        review_block_reason = "Log in after buying this product to leave a verified review."
    elif user_review_exists:
        review_block_reason = "You have already reviewed this product."
    elif not has_bought_product:
        review_block_reason = "Only customers who bought this product can leave a review."

    context = {
        "product": product,
        "product_volumes": product_volumes,
        "cart_count": cart_count,
        "reviews": page_obj,
        "verified_reviews_count": reviews.count(),
        "average_rating": round(average_rating, 1) if average_rating else None,
        "product_images": product_images,
        "can_review": can_review,
        "has_bought_product": has_bought_product,
        "user_review_exists": user_review_exists,
        "review_block_reason": review_block_reason,
    }
    return render(request, "orders/product_detail.html", context)


# =================================== Products Detail for quests not signed in ===================================
def product_details_view(request, product_uuid):
    try:
        product = (
            Product.objects.select_related("category", "supplier")
            .prefetch_related("images")
            .get(uuid=product_uuid)
        )
        product_volumes = ProductVolume.objects.filter(
            product=product, is_active=True
        ).filter(
            Q(stock_quantity__isnull=True) | Q(stock_quantity__gt=0)
        ).order_by(
            "sort_order", "volume__ml", "product_type"
        )
        reviews = Review.objects.filter(product=product, is_verified=True).order_by(
            "-created_at"
        )
        average_rating = reviews.aggregate(value=Avg("rating"))["value"]

        paginator = Paginator(reviews, 5)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        for review in page_obj:
            review.filled_stars = "★" * review.rating
            review.empty_stars = "☆" * (5 - review.rating)

        for review in page_obj:
            review.filled_stars = range(review.rating)
            review.empty_stars = range(5 - review.rating)

        verified_reviews_count = reviews.filter(is_verified=True).count()
        product_images = product.image_urls

        context = {
            "product": product,
            "product_id": product.id,
            "name": product.name,
            "gender": product.gender,
            "description": product.description,
            "category": product.category.name if product.category else "N/A",
            "supplier": product.supplier,
            "volumes": [],
            "reviews": page_obj,
            "verified_reviews_count": verified_reviews_count,
            "average_rating": round(average_rating, 1) if average_rating else None,
            "product_images": product_images,
            "product_uuid": str(product_uuid),
        }

        for product_volume in product_volumes:
            volume = product_volume.volume
            discount_value = product_volume.discount_value or 0
            # Use a remote placeholder if image is missing so storefront partials do not depend on local static assets.
            image_url = (
                volume.image.url
                if volume.image
                else "https://placehold.co/600x600/f8fafc/111827?text=Jobell"
            )
            volume_data = {
                "id": product_volume.id,
                "ml": product_volume.volume.ml,
                "price": float(product_volume.effective_price),
                "original_price": float(product_volume.original_price),
                "image": product_volume.image_url or image_url,
                "product_type": product_volume.product_type,
                "discount_value": float(discount_value),
                "discounted_price": float(product_volume.current_price),
                "current_price": float(product_volume.current_price),
                "variant_label": product_volume.variant_label,
                "stock": product_volume.available_quantity,
                "max_quantity_per_order": product_volume.max_quantity_per_order,
            }
            context["volumes"].append(volume_data)

        return render(request, "orders/product_detail_partial.html", context)
    except Product.DoesNotExist:
        return render(
            request,
            "orders/product_detail_partial.html",
            {"error": "Product not found"},
        )


# ================================ Products Wishlist ===================================
@login_required
def wishlist_add(request, product_uuid):
    # Get the product object
    product = get_object_or_404(Product, uuid=product_uuid)

    # Check if the product is already in the user's wishlist
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user, product=product
    )

    if created:
        # Product added to wishlist
        messages.success(
            request,
            f"Product '{product.name}' has been added to your wishlist!",
            extra_tags="bg-success",
        )
    else:
        # Product already in wishlist
        messages.info(
            request,
            f"Product '{product.name}' is already in your wishlist.",
            extra_tags="bg-warning",
        )

    return redirect(
        _safe_redirect_target(
            request,
            reverse("orders:product_detail", kwargs={"product_uuid": product.uuid}),
        )
    )


# =================================== wishlist_view ===================================
@login_required
def wishlist_view(request):
    # Fetch all the products in the user's wishlist
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related("product", "product__category").prefetch_related("product__images")

    # Paginate the wishlist items (10 items per page)
    paginator = Paginator(wishlist_items, 12)  # Show 12 wishlist items per page
    page_number = request.GET.get(
        "page"
    )  # Get the current page number from the request
    page_obj = paginator.get_page(page_number)  # Get the page object

    # Fetch the default image for each product in the wishlist
    for item in page_obj:
        item.default_image = ProductImage.objects.filter(
            product=item.product, is_default=True
        ).first()
        item.product_info = build_storefront_product_card(item.product)

    # Pass the page object to the template
    context = {"page_obj": page_obj}
    return render(request, "orders/wishlist.html", context)


# =================================== remove_from_wishlist ===================================


@login_required
def remove_from_wishlist(request, wishlist_item_id):
    try:
        # Check if the wishlist item exists for the logged-in user
        wishlist_item = Wishlist.objects.get(id=wishlist_item_id, user=request.user)
    except Wishlist.DoesNotExist:
        messages.error(
            request, "Product not found in your wishlist.", extra_tags="bg-danger"
        )
        return redirect("orders:wishlist")

    # Remove the wishlist item
    wishlist_item.delete()
    messages.success(
        request, "Product has been removed from your wishlist.", extra_tags="bg-success"
    )

    return redirect("orders:wishlist")


# =================================== add_to_cart ===================================
# @login_required
# def add_to_cart(request, product_uuid):
#     product = get_object_or_404(Product, uuid=product_uuid)
#     cart, created = Cart.objects.get_or_create(user=request.user)
#     quantity = int(request.POST.get("quantity", 1))
#     volume_id = request.POST.get("volume_id")

#     # Validate the volume
#     if not volume_id:
#         messages.error(request, "Please select a product volume.")
#         return redirect("orders:product_detail", product_uuid=product_uuid)

#     # Fetch the selected volume
#     volume = get_object_or_404(ProductVolume, id=volume_id)

#     if quantity <= 0:
#         messages.add_message(
#             request,
#             messages.ERROR,
#             "Invalid quantity. It must be greater than zero.",
#             extra_tags="bg-danger text-white",
#         )
#         return redirect("orders:product_detail", product_uuid=product_uuid)

#     try:
#         # Add volume to the CartItem creation or retrieval
#         cart_item, created = CartItem.objects.get_or_create(
#             cart=cart, product=product, volume=volume
#         )
#     except MultipleObjectsReturned:
#         cart_item = CartItem.objects.filter(
#             cart=cart, product=product, volume=volume
#         ).first()

#     if not created:
#         cart_item.quantity += quantity
#         cart_item.save()
#         messages.add_message(
#             request,
#             messages.INFO,
#             f"Increased quantity of {product.name} ({volume.volume.ml} ML) to {cart_item.quantity} in your cart.",
#             extra_tags="bg-info text-white",
#         )
#     else:
#         cart_item.quantity = quantity
#         cart_item.save()
#         messages.add_message(
#             request,
#             messages.SUCCESS,
#             f"{product.name} ({volume.volume.ml} ML) has been added to your cart with quantity {quantity}.",
#             extra_tags="bg-success text-white",
#         )

#     return redirect("orders:product_detail", product_uuid=product_uuid)


# def add_to_cart(request, product_uuid):
#     product = get_object_or_404(Product, uuid=product_uuid)
#     quantity = int(request.POST.get("quantity", 1))
#     volume_id = request.POST.get("volume_id")

#     # Validate volume
#     if not volume_id:
#         messages.error(request, "Please select a product volume.")
#         return redirect("orders:product_detail", product_uuid=product_uuid)

#     volume = get_object_or_404(ProductVolume, id=volume_id)

#     # Validate quantity
#     if quantity <= 0:
#         messages.error(
#             request,
#             "Quantity must be greater than zero.",
#             extra_tags="bg-danger text-white",
#         )
#         return redirect("orders:product_detail", product_uuid=product_uuid)

#     # Check stock (assuming ProductVolume has a stock field)
#     if hasattr(volume, "stock") and volume.stock < quantity:
#         messages.error(
#             request,
#             f"Only {volume.stock} units available.",
#             extra_tags="bg-danger text-white",
#         )
#         return redirect("orders:product_detail", product_uuid=product_uuid)

#     # Get or create cart
#     if request.user.is_authenticated:
#         cart, _ = Cart.objects.get_or_create(user=request.user)
#     else:
#         cart_id = request.session.get("cart_id")
#         if cart_id:
#             cart = get_object_or_404(Cart, id=cart_id, user=None)
#         else:
#             cart = Cart.objects.create(user=None)
#             request.session["cart_id"] = cart.id
#             request.session.modified = True

#     # Add or update cart item
#     cart_item, created = CartItem.objects.get_or_create(
#         cart=cart, product=product, volume=volume
#     )
#     if not created:
#         new_quantity = cart_item.quantity + quantity
#         if hasattr(volume, "stock") and new_quantity > volume.stock:
#             messages.error(
#                 request,
#                 f"Cannot add {new_quantity} units. Only {volume.stock} available.",
#                 extra_tags="bg-danger text-white",
#             )
#             return redirect("orders:product_detail", product_uuid=product_uuid)
#         cart_item.quantity = new_quantity
#         messages.info(
#             request,
#             f"Increased {product.name} ({volume.volume.ml}ml) to {new_quantity} in cart.",
#             extra_tags="bg-info text-white",
#         )
#     else:
#         cart_item.quantity = quantity
#         messages.success(
#             request,
#             f"Added {quantity} x {product.name} ({volume.volume.ml}ml) to cart.",
#             extra_tags="bg-success text-white",
#         )
#     cart_item.save()

#     return redirect("orders:product_detail", product_uuid=product_uuid)


def add_to_cart(request, product_uuid):
    product = get_object_or_404(Product, uuid=product_uuid)
    wants_json = _wants_json(request)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        quantity = 0
    volume_id = request.POST.get("volume_id")
    fallback_url = reverse("orders:product_detail", kwargs={"product_uuid": product_uuid})

    # Validate volume
    if not volume_id:
        if wants_json:
            return JsonResponse(
                {"ok": False, "message": "Please select a product volume."},
                status=400,
            )
        messages.error(request, "Please select a product volume.")
        return redirect(_safe_redirect_target(request, fallback_url))

    volume = get_object_or_404(ProductVolume, id=volume_id, product=product)

    if not volume.is_active:
        if wants_json:
            return JsonResponse(
                {
                    "ok": False,
                    "message": "This product option is currently unavailable.",
                },
                status=400,
            )
        messages.error(
            request,
            "This product option is currently unavailable.",
            extra_tags="bg-danger text-white",
        )
        return redirect(_safe_redirect_target(request, fallback_url))

    # Validate quantity
    if quantity <= 0:
        if wants_json:
            return JsonResponse(
                {"ok": False, "message": "Quantity must be greater than zero."},
                status=400,
            )
        messages.error(
            request,
            "Quantity must be greater than zero.",
            extra_tags="bg-danger text-white",
        )
        return redirect(_safe_redirect_target(request, fallback_url))

    # Check stock and per-order limits from the product variation.
    if volume.available_quantity < quantity:
        if wants_json:
            return JsonResponse(
                {
                    "ok": False,
                    "message": f"Only {volume.available_quantity} units available.",
                },
                status=400,
            )
        messages.error(
            request,
            f"Only {volume.available_quantity} units available.",
            extra_tags="bg-danger text-white",
        )
        return redirect(_safe_redirect_target(request, fallback_url))

    if volume.max_quantity_per_order and quantity > volume.max_quantity_per_order:
        if wants_json:
            return JsonResponse(
                {
                    "ok": False,
                    "message": (
                        f"You can add up to {volume.max_quantity_per_order} units "
                        "of this option per order."
                    ),
                },
                status=400,
            )
        messages.error(
            request,
            f"You can add up to {volume.max_quantity_per_order} units of this option per order.",
            extra_tags="bg-danger text-white",
        )
        return redirect(_safe_redirect_target(request, fallback_url))

    cart = get_or_create_cart(request)

    # Add or update cart item
    with transaction.atomic():
        cart_item, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart,
            volume=volume,
            defaults={"product": product, "quantity": 0},
        )
        new_quantity = cart_item.quantity + quantity
        if new_quantity > volume.available_quantity:
            if wants_json:
                return _cart_json_response(
                    cart,
                    (
                        f"Cannot add {new_quantity} units. "
                        f"Only {volume.available_quantity} available."
                    ),
                    status=400,
                )
            messages.error(
                request,
                f"Cannot add {new_quantity} units. Only {volume.available_quantity} available.",
                extra_tags="bg-danger text-white",
            )
            return redirect(_safe_redirect_target(request, fallback_url))
        cart_item.product = product
        cart_item.quantity = new_quantity
        cart_item.save()

    if wants_json:
        return _cart_json_response(cart)

    if created:
        messages.success(
            request,
            f"Added {quantity} x {product.name} ({volume.volume.ml}ml) to cart.",
            extra_tags="bg-success text-white",
        )
    else:
        messages.info(
            request,
            f"Increased {product.name} ({volume.volume.ml}ml) to {cart_item.quantity} in cart.",
            extra_tags="bg-info text-white",
        )

    return redirect(_safe_redirect_target(request, fallback_url))


# =================================== cart_view ===================================
# @login_required
# def cart_view(request):
#     cart, created = Cart.objects.get_or_create(user=request.user)

#     total_price = sum(item.get_total_price() for item in cart.items.select_related("product", "volume", "volume__volume"))

#     context = {
#         "cart": cart,
#         "total_price": total_price,
#     }

#     return render(request, "orders/cart.html", context)


# def cart_view(request):
#     # Get or create cart
#     if request.user.is_authenticated:
#         cart, created = Cart.objects.get_or_create(user=request.user)
#     else:
#         cart_id = request.session.get("cart_id")
#         if cart_id:
#             cart = get_object_or_404(Cart, id=cart_id, user=None)
#         else:
#             cart = Cart.objects.create(user=None)
#             request.session["cart_id"] = cart.id
#             request.session.modified = True

#     total_price = sum(item.get_total_price() for item in cart.items.select_related("product", "volume", "volume__volume"))

#     context = {
#         "cart": cart,
#         "total_price": total_price,
#     }

#     return render(request, "orders/cart.html", context)


def cart_view(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related(
        "product",
        "product__category",
        "volume",
        "volume__volume",
    )
    total_price = cart_total(cart)
    total_items = sum(item.quantity for item in cart_items)

    context = {
        "cart": cart,
        "cart_items": cart_items,
        "total_price": total_price,
        "total_items": total_items,
    }

    return render(request, "orders/cart.html", context)


# @login_required
# def update_cart(request, item_id):
#     cart = get_object_or_404(Cart, user=request.user)
#     item = get_object_or_404(CartItem.objects.select_related("product", "volume", "volume__volume"), id=item_id, cart=cart)

#     if request.method == "POST":
#         quantity = int(request.POST.get("quantity", 1))

#         if quantity > 0:
#             item.quantity = quantity
#             item.save()
#             messages.success(
#                 request, "Cart updated successfully.", extra_tags="bg-success"
#             )
#         else:
#             messages.error(
#                 request, "Quantity must be at least 1.", extra_tags="bg-danger"
#             )

#     return redirect("orders:cart")

# @login_required
# def remove_from_cart(request, item_id):
#     cart = get_object_or_404(Cart, user=request.user)
#     item = get_object_or_404(CartItem.objects.select_related("product", "volume", "volume__volume"), id=item_id, cart=cart)

#     item.delete()
#     messages.success(request, "Item removed from cart.", extra_tags="bg-success")

#     return redirect("orders:cart")


# def update_cart(request, item_id):
#     # Get the cart
#     if request.user.is_authenticated:
#         cart = get_object_or_404(Cart, user=request.user)
#     else:
#         cart_id = request.session.get("cart_id")
#         if not cart_id:
#             messages.error(request, "No cart found.", extra_tags="bg-danger text-white")
#             return redirect("orders:cart")
#         cart = get_object_or_404(Cart, id=cart_id, user=None)

#     # Get the cart item and verify ownership
#     item = get_object_or_404(CartItem.objects.select_related("product", "volume", "volume__volume"), id=item_id, cart=cart)

#     if request.method == "POST":
#         quantity = int(request.POST.get("quantity", 1))

#         # Validate stock (assuming ProductVolume has a stock field)
#         if hasattr(item.volume, "stock") and quantity > item.volume.stock:
#             messages.error(
#                 request,
#                 f"Cannot update to {quantity} units. Only {item.volume.stock} available.",
#                 extra_tags="bg-danger text-white",
#             )
#         elif quantity > 0:
#             item.quantity = quantity
#             item.save()
#             messages.success(
#                 request,
#                 f"Updated {item.product.name} quantity to {quantity}.",
#                 extra_tags="bg-success text-white",
#             )
#         else:
#             item.delete()
#             messages.success(
#                 request,
#                 f"Removed {item.product.name} from cart.",
#                 extra_tags="bg-success text-white",
#             )

#     return redirect("orders:cart")


# def remove_from_cart(request, item_id):
#     # Get the cart
#     if request.user.is_authenticated:
#         cart = get_object_or_404(Cart, user=request.user)
#     else:
#         cart_id = request.session.get("cart_id")
#         if not cart_id:
#             messages.error(request, "No cart found.", extra_tags="bg-danger text-white")
#             return redirect("orders:cart")
#         cart = get_object_or_404(Cart, id=cart_id, user=None)

#     # Get the cart item and verify ownership
#     item = get_object_or_404(CartItem.objects.select_related("product", "volume", "volume__volume"), id=item_id, cart=cart)

#     product_name = item.product.name
#     item.delete()
#     messages.success(
#         request,
#         f"Removed {product_name} from cart.",
#         extra_tags="bg-success text-white",
#     )

#     return redirect("orders:cart")


def update_cart(request, item_id):
    cart = get_or_create_cart(request)

    # Get the cart item and verify ownership
    item = get_object_or_404(CartItem.objects.select_related("product", "volume", "volume__volume"), id=item_id, cart=cart)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))

        # Validate stock against the selected product variation.
        if quantity > item.volume.available_quantity:
            messages.error(
                request,
                f"Cannot update to {quantity} units. Only {item.volume.available_quantity} available.",
                extra_tags="bg-danger text-white",
            )
        elif (
            item.volume.max_quantity_per_order
            and quantity > item.volume.max_quantity_per_order
        ):
            messages.error(
                request,
                f"You can keep up to {item.volume.max_quantity_per_order} units of this option in one order.",
                extra_tags="bg-danger text-white",
            )
        elif quantity > 0:
            item.quantity = quantity
            item.save()
            messages.success(
                request,
                f"Updated {item.product.name} quantity to {quantity}.",
                extra_tags="bg-success text-white",
            )
        else:
            item.delete()
            messages.success(
                request,
                f"Removed {item.product.name} from cart.",
                extra_tags="bg-success text-white",
            )

    return redirect("orders:cart")


def remove_from_cart(request, item_id):
    cart = get_or_create_cart(request)

    # Get the cart item and verify ownership
    item = get_object_or_404(CartItem.objects.select_related("product", "volume", "volume__volume"), id=item_id, cart=cart)

    product_name = item.product.name
    item.delete()
    messages.success(
        request,
        f"Removed {product_name} from cart.",
        extra_tags="bg-success text-white",
    )

    return redirect("orders:cart")


# def send_order_email(
#     recipient_name,
#     recipient_email,
#     order_id,
#     order_details,
#     order_status,
#     total_price,
#     is_customer=True,
# ):
#     customer_order_history_url = "https://jobellinc.com/orders/order-history/"
#     orders_to_be_processed_url = "https://jobellinc.com/orders/to-be-processed/"
#     subject = "Your Order has been Placed" if is_customer else "New Order to Process"

#     if is_customer:
#         email_body = f"""
#         <html>
#             <body style="font-family: Arial, sans-serif; color: #333;">
#                 <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px; background-color: #f9f9f9;">
#                     <h2 style="color: #2E86C1; text-align: center;">Thank You for Your Purchase!</h2>
#                     <p>Dear <strong>{recipient_name}</strong>,</p>
#                     <p>Thank you for placing your order with us! We appreciate your trust in our products and services. Your order has been successfully received and is being processed. Here are the details of your order:</p>

#                     <h4>Order ID: <strong>{order_id}</strong> | Status: <span style="color: #FF5733;">{order_status}</span></h4>

#                     <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
#                         <tr style="background-color: #f2f2f2;">
#                             <th style="padding: 10px; border: 1px solid #ddd;">Product</th>
#                             <th style="padding: 10px; border: 1px solid #ddd;">Volume</th>
#                             <th style="padding: 10px; border: 1px solid #ddd;">Qty</th>
#                             <th style="padding: 10px; border: 1px solid #ddd;">Price @</th>
#                             <th style="padding: 10px; border: 1px solid #ddd;">Image</th>
#                         </tr>
#                         {''.join(
#                             f"""
#                             <tr>
#                                 <td style="padding: 10px; border: 1px solid #ddd;">{item['product_name']}</td>
#                                 <td style="padding: 10px; border: 1px solid #ddd;">{item['volume']} ML</td>
#                                 <td style="padding: 10px; border: 1px solid #ddd;">{item['quantity']}</td>
#                                 <td style="padding: 10px; border: 1px solid #ddd;">UgX {item['price']:,.2f}</td>
#                                 <td style="padding: 10px; border: 1px solid #ddd;">
#                                     <img src="{item['image_url']}" alt="{item['product_name']}" style="width: 50px; height: auto; border-radius: 5px;">
#                                 </td>
#                             </tr>
#                             """ for item in order_details
#                         )}
#                     </table>

#                     <h3 style="text-align: right; color: #2E86C1;">Total Price: UgX {total_price:,.2f}</h3>

#                     <div style="text-align: center; margin: 20px 0;">
#                         <a href="{customer_order_history_url}" style="background-color: #2E86C1; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px;">View Order History</a>
#                     </div>

#                     <p>Thank you for shopping with us!</p>
#                     <p style="color: #888;">- Jobel Inc Management</p>
#                 </div>
#             </body>
#         </html>

#         """
#     else:
#         email_body = f"""
#         <html>
#         <body style="font-family: Arial, sans-serif; color: #333;">
#             <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
#                 <h2 style="color: #C0392B; text-align: center;">New Order to Process</h2>
#                 <p>Hello <strong>Jobel Inc Team</strong>,</p>
#                 <p>A new order has been placed. The order ID is <strong>{order_id}</strong>. Please review and process the order by clicking the button below:</p>
#                 <div style="text-align: center; margin: 20px 0;">
#                     <a href="{orders_to_be_processed_url}" style="background-color: #C0392B; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px;">Process Order</a>
#                 </div>
#                 <p>Thanks for your prompt attention!</p>
#                 <p style="color: #888;">- Jobel Inc Management</p>
#             </div>
#         </body>
#         </html>
#         """

#     from_email = getattr(settings, "EMAIL_HOST_USER", None)
#     to = [recipient_email]

#     # Send HTML email
#     try:
#         email = EmailMultiAlternatives(subject, strip_tags(email_body), from_email, to)
#         email.attach_alternative(email_body, "text/html")
#         email.send()
#         logger.info(
#             f"Order email sent successfully to {recipient_email} for Order #{order_id}"
#         )
#         return True
#     except Exception as e:
#         logger.error(f"Error sending email to {recipient_email}: {str(e)}")
#         return False


# =================================== checkout_view ===================================
# @login_required
# def checkout_view(request):
#     try:
#         cart = Cart.objects.get(user=request.user)
#     except Cart.DoesNotExist:
#         messages.error(request, "Your cart is empty.")
#         return redirect("orders:cart")  # Redirect to cart view if the cart is empty

#     customer, created = Customer.objects.get_or_create(user=request.user)

#     total_price = sum(
#         item.get_total_price() for item in cart.items.all()
#     )  # Calculate total price

#     if request.method == "POST":
#         form = CheckoutForm(request.POST)
#         if form.is_valid():
#             total_amount = total_price  # Use total_price here

#             # Update customer details
#             customer.first_name = form.cleaned_data["first_name"]
#             customer.last_name = form.cleaned_data["last_name"]
#             customer.email = form.cleaned_data["email"]
#             customer.mobile = form.cleaned_data["mobile"]
#             customer.address = form.cleaned_data["address"]
#             customer.save()

#             # Create the order
#             order = Order.objects.create(
#                 customer=customer,
#                 created_at=timezone.now(),
#                 total_amount=total_amount,
#                 status="Pending",
#             )

#             order_details = []  # Initialize order_details list

#             # Create OrderDetail entries
#             for item in cart.items.all():
#                 product_volume = item.volume
#                 discounted_price = product_volume.get_discounted_price()
#                 image_url = (
#                     product_volume.volume.image.url
#                     if product_volume.volume.image
#                     else ""
#                 )

#                 order_details.append(
#                     {
#                         "product_name": item.product.name,
#                         "volume": item.volume.volume.ml,
#                         "quantity": item.quantity,
#                         "price": discounted_price,
#                         "image_url": image_url,
#                         "order_status": order.status,
#                     }
#                 )

#                 OrderDetail.objects.create(
#                     order=order,
#                     product=item.product,
#                     product_volume=item.volume,
#                     quantity=item.quantity,
#                     discounted_price=discounted_price,
#                     price=item.volume.volume.price,
#                 )

#             # Clear cart after checkout
#             cart.items.all().delete()

#             # Send confirmation emails
#             send_order_email(
#                 customer.first_name,
#                 customer.email,
#                 order.id,
#                 order_details,
#                 order.status,
#                 total_price,
#                 is_customer=True,
#             )
#             send_order_email(
#                 "Jobel Inc",
#                 settings.EMAIL_HOST_USER,
#                 order.id,
#                 order_details,
#                 order.status,
#                 total_price,
#                 is_customer=False,
#             )

#             messages.success(
#                 request,
#                 f"Your order has been placed successfully! Order ID: {order.id}",
#             )
#             return redirect("orders:order_confirmation", order_id=order.id)

#     else:
#         form = CheckoutForm(
#             initial={
#                 "first_name": customer.first_name,
#                 "last_name": customer.last_name,
#                 "email": customer.email,
#                 "mobile": customer.mobile,
#                 "address": customer.address,
#             }
#         )

#     return render(
#         request,
#         "orders/checkout.html",
#         {"form": form, "cart": cart, "total_price": total_price},
#     )
def _checkout_addresses_for(request):
    if not request.user.is_authenticated:
        return []
    return [
        {
            "id": address.pk,
            "phone_number": address.phone_number,
            "street_name": address.street_name,
            "region": address.region,
            "city": address.city,
            "area": address.area,
        }
        for address in CustomerAddress.objects.filter(user=request.user)
    ]


def _checkout_context(
    request,
    *,
    form,
    cart,
    subtotal,
    shipping_fee,
    grand_total,
    delivery_available=True,
    delivery_quote_message="",
):
    return {
        "form": form,
        "cart": cart,
        "total_price": subtotal,
        "shipping_fee": shipping_fee,
        "grand_total": grand_total,
        "delivery_available": delivery_available,
        "delivery_quote_message": delivery_quote_message,
        "checkout_addresses": _checkout_addresses_for(request),
    }


def _has_location_override(saved_address, region, city, area):
    if not saved_address:
        return False
    return any(
        [
            (region or "") and region != saved_address.region,
            (city or "").strip().casefold() != (saved_address.city or "").strip().casefold(),
            (area or "").strip().casefold() != (saved_address.area or "").strip().casefold(),
        ]
    )


def checkout_delivery_summary(request):
    cart = get_or_create_cart(request)
    cart = Cart.objects.prefetch_related("items__volume").filter(pk=cart.pk).first()
    if not cart or not cart.items.exists():
        return JsonResponse(
            {
                "available": False,
                "message": "Your cart is empty.",
                "subtotal": "0.00",
                "shipping_fee": "0.00",
                "grand_total": "0.00",
            },
            status=400,
        )

    shipping_method = request.GET.get("shipping_method", "delivery")
    subtotal = cart_total(cart)
    if shipping_method == "pickup":
        return JsonResponse(
            {
                "available": True,
                "message": "Pickup is free.",
                "match_level": "pickup",
                "subtotal": f"{subtotal:.2f}",
                "shipping_fee": "0.00",
                "grand_total": f"{subtotal:.2f}",
            }
        )

    saved_address = None
    saved_address_id = request.GET.get("saved_address")
    if saved_address_id and request.user.is_authenticated:
        saved_address = CustomerAddress.objects.filter(
            pk=saved_address_id, user=request.user
        ).first()

    request_region = request.GET.get("delivery_region", "")
    request_city = request.GET.get("delivery_city", "")
    request_area = request.GET.get("delivery_area", "")
    if saved_address and not _has_location_override(
        saved_address, request_region, request_city, request_area
    ):
        region = saved_address.region
        city = saved_address.city
        area = saved_address.area
    else:
        region = request_region
        city = request_city
        area = request_area

    quote = delivery_quote_for(region, city, area)
    return JsonResponse(
        {
            "available": quote.available,
            "message": quote.message,
            "match_level": quote.match_level,
            "subtotal": f"{subtotal:.2f}",
            "shipping_fee": f"{quote.fee:.2f}",
            "grand_total": f"{subtotal + quote.fee:.2f}",
        },
    )


def checkout_view(request):
    cart = get_or_create_cart(request)
    cart = (
        Cart.objects.prefetch_related("items__product", "items__volume__volume")
        .filter(pk=cart.pk)
        .first()
    )
    if not cart or not cart.items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("orders:cart")  # Redirect to cart view if the cart is empty

    customer = None
    if request.user.is_authenticated:
        customer, created = Customer.objects.get_or_create(
            user=request.user,
            defaults={
                "first_name": request.user.first_name or request.user.username,
                "last_name": request.user.last_name,
                "email": request.user.email,
            },
        )
    subtotal = cart_total(cart)
    shipping_fee = Decimal("0.00")
    grand_total = subtotal
    delivery_quote_message = ""
    delivery_available = True

    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            saved_address = form.cleaned_data.get("saved_address")
            update_saved_address = request.POST.get("update_saved_address") == "1"
            shipping_method = form.cleaned_data.get("shipping_method", "delivery")
            pickup_station = form.cleaned_data.get("pickup_station")
            form_delivery_region = form.cleaned_data["delivery_region"]
            form_delivery_city = form.cleaned_data["delivery_city"]
            form_delivery_area = form.cleaned_data.get("delivery_area", "")
            has_location_override = _has_location_override(
                saved_address,
                form_delivery_region,
                form_delivery_city,
                form_delivery_area,
            )
            if saved_address and not update_saved_address and not has_location_override:
                delivery_region = saved_address.region
                delivery_city = saved_address.city
                delivery_area = saved_address.area
                delivery_address_text = saved_address.single_line
                contact_phone = saved_address.phone_number or form.cleaned_data["mobile"]
            else:
                delivery_region = form_delivery_region
                delivery_city = form_delivery_city
                delivery_area = form_delivery_area
                delivery_address_text = form.cleaned_data["address"]
                contact_phone = form.cleaned_data["mobile"]

            if shipping_method == "pickup":
                shipping_fee = Decimal("0.00")
            else:
                delivery_quote = delivery_quote_for(
                    delivery_region, delivery_city, delivery_area
                )
                shipping_fee = delivery_quote.fee
                delivery_available = delivery_quote.available
                delivery_quote_message = delivery_quote.message
                if not delivery_quote.available:
                    form.add_error("delivery_area", delivery_quote.message)
                    grand_total = subtotal
                    return render(
                        request,
                        "orders/checkout.html",
                        _checkout_context(
                            request,
                            form=form,
                            cart=cart,
                            subtotal=subtotal,
                            shipping_fee=shipping_fee,
                            grand_total=grand_total,
                            delivery_available=delivery_available,
                            delivery_quote_message=delivery_quote_message,
                        ),
                    )
            grand_total = subtotal + shipping_fee
            customer_data = {
                "first_name": form.cleaned_data["first_name"],
                "last_name": form.cleaned_data["last_name"],
                "email": form.cleaned_data["email"],
                "mobile": contact_phone,
                "address": (
                    f"Pickup: {pickup_station}"
                    if shipping_method == "pickup" and pickup_station
                    else delivery_address_text
                ),
            }
            try:
                order = create_order_from_cart(
                    cart,
                    customer_data=customer_data,
                    payment_method=form.cleaned_data.get("payment_method", "cod"),
                    mobile_money_number=form.cleaned_data.get(
                        "mobile_money_number", ""
                    ),
                    shipping_data={
                        "shipping_method": shipping_method,
                        "shipping_fee": shipping_fee,
                        "delivery_address_text": delivery_address_text,
                        "delivery_region": delivery_region,
                        "pickup_station": pickup_station,
                    },
                )
            except (ValueError, ValidationError) as exc:
                messages.error(request, exc, extra_tags="bg-danger text-white")
                return redirect("orders:cart")

            if request.user.is_authenticated and shipping_method == "delivery":
                if saved_address and update_saved_address:
                    saved_address.street_name = delivery_address_text
                    saved_address.city = delivery_city
                    saved_address.area = delivery_area
                    saved_address.phone_number = contact_phone
                    saved_address.region = delivery_region
                    if form.cleaned_data.get("save_address"):
                        CustomerAddress.objects.filter(
                            user=request.user, is_default=True
                        ).exclude(pk=saved_address.pk).update(is_default=False)
                        saved_address.is_default = True
                    saved_address.save()
                elif form.cleaned_data.get("save_address") and not saved_address:
                    CustomerAddress.objects.create(
                        user=request.user,
                        street_name=delivery_address_text,
                        city=delivery_city,
                        area=delivery_area,
                        phone_number=contact_phone,
                        region=delivery_region,
                        is_default=not CustomerAddress.objects.filter(
                            user=request.user, is_default=True
                        ).exists(),
                    )

            placed_order_ids = request.session.get("placed_order_ids", [])
            placed_order_ids.append(order.id)
            request.session["placed_order_ids"] = placed_order_ids[-10:]
            request.session.modified = True

            messages.success(
                request,
                f"Your order has been placed successfully! Order ID: {order.id}",
                extra_tags="bg-success",
            )
            return redirect("orders:order_confirmation", order_id=order.id)

    else:
        default_address = (
            CustomerAddress.objects.filter(user=request.user, is_default=True).first()
            if request.user.is_authenticated
            else None
        )
        if default_address:
            delivery_quote = delivery_quote_for(
                default_address.region,
                default_address.city,
                default_address.area,
            )
            shipping_fee = delivery_quote.fee
            delivery_available = delivery_quote.available
            delivery_quote_message = delivery_quote.message
            grand_total = subtotal + shipping_fee
        form = CheckoutForm(
            initial={
                "first_name": customer.first_name if customer else "",
                "last_name": customer.last_name if customer else "",
                "email": customer.email if customer else "",
                "mobile": (
                    default_address.phone_number
                    if default_address and default_address.phone_number
                    else customer.mobile if customer else ""
                ),
                "address": default_address.street_name if default_address else customer.address if customer else "",
                "delivery_region": default_address.region if default_address else CustomerAddress.Region.KAMPALA_AREA,
                "delivery_city": default_address.city if default_address else "",
                "delivery_area": default_address.area if default_address else "",
                "saved_address": default_address.pk if default_address else None,
            },
            user=request.user,
        )

    return render(
        request,
        "orders/checkout.html",
        _checkout_context(
            request,
            form=form,
            cart=cart,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            grand_total=grand_total,
            delivery_available=delivery_available,
            delivery_quote_message=delivery_quote_message,
        ),
    )


# =================================== process_payment ===================================
@login_required
def process_payment(request, order_id):
    """
    Handles the payment processing for a given order.
    """
    order = get_object_or_404(Order, id=order_id, customer__user=request.user)
    form_title = "Payment Details"

    # Retrieve the customer's phone number
    phone_number = order.customer.mobile
    if not phone_number:
        return JsonResponse(
            {"error": "The customer does not have a valid mobile number."}, status=400
        )

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")
        logger.debug(f"Payment Method: {payment_method}, Phone Number: {phone_number}")

        # Prepare payment data
        payment_data = {
            "amount": float(order.total_amount),
            "currency": "EUR",
            "externalId": str(order.id),
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone_number,
            },
            "payerMessage": f"Payment for Order #{order.id}",
            "payeeMessage": "Payment received",
        }

        # Fetch access token
        access_token = get_access_token()
        if not access_token:
            return JsonResponse(
                {"error": "Failed to authenticate with the payment service."},
                status=500,
            )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": settings.MTN_SUBSCRIPTION_KEY,
        }

        try:
            # Make the payment request
            response = requests.post(
                "https://sandbox.momodeveloper.mtn.com/collection/v1_0/requesttopay",
                headers=headers,
                json=payment_data,
            )
            response.raise_for_status()

            if (
                response.status_code == 202
            ):  # MoMo typically returns 202 for accepted requests
                transaction_info = response.json()
                order.transaction_id = transaction_info.get("transactionId")
                order.payment_status = "pending"
                order.save()
                return redirect("orders:customer_order_history")
            else:
                logger.error(f"Payment failed: {response.text}")
                order.payment_status = "failed"
                order.save()
                return JsonResponse(
                    {"error": "Payment failed. Please try again."}, status=400
                )

        except requests.exceptions.RequestException as req_err:
            logger.error(f"Request error occurred: {req_err}")
            order.payment_status = "failed"
            order.save()
            return JsonResponse(
                {"error": "Payment failed due to server error. Please try again."},
                status=500,
            )

    # Render the payment form
    return render(
        request,
        "orders/payment.html",
        {
            "order": order,
            "form_title": form_title,
            "payment_method_choices": Order.PAYMENT_METHOD_CHOICES,
        },
    )


def get_access_token():
    """
    Fetches the access token for MTN API using Basic Authentication.
    """
    client_id = settings.MTN_CLIENT_ID
    client_secret = settings.MTN_CLIENT_SECRET
    subscription_key = settings.MTN_SUBSCRIPTION_KEY

    if not client_id or not client_secret or not subscription_key:
        logger.error("MTN API credentials are missing in settings.")
        return None

    url = "https://sandbox.momodeveloper.mtn.com/collection/token/"
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_credentials}",
        "Ocp-Apim-Subscription-Key": subscription_key,
    }

    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        return response.json().get("access_token")
    except requests.RequestException as e:
        logger.error(f"Error fetching access token: {e}")
        return None


# =================================== confirm_payment ===================================
def confirm_payment_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer__user=request.user)
    customer = order.customer

    # Update payment status
    order.payment_status = "completed"
    order.save()

    # Prepare the context
    context = {
        "order": order,
        "customer": customer,
    }

    # Add success message
    messages.success(request, "Payment made successfully", extra_tags="bg-success")

    return render(request, "orders/customer_order_history.html", context)


# =================================== payment_flutter_view ===================================
@login_required
def payment_flutter_view(request):
    unique_tx_ref = f"txref-{uuid.uuid4()}"  # Generate a unique transaction reference
    context = {
        "unique_tx_ref": unique_tx_ref,
        "public_key": getattr(settings, "FLUTTERWAVE_PUBLIC_KEY", ""),
        "currency": "UGX",
        "form_title": "Secure Flutterwave Payment",
    }
    return render(request, "orders/payment_flutter.html", context)


# =================================== order_confirmation_view ===================================
def order_confirmation_view(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("customer", "pickup_station").prefetch_related(
            "details__product",
            "details__product_volume__volume",
        ),
        id=order_id,
    )
    is_owner = request.user.is_authenticated and order.customer.user == request.user
    is_session_order = order.id in request.session.get("placed_order_ids", [])
    if not (is_owner or is_session_order):
        messages.error(request, "We could not verify access to that order.")
        return redirect("orders:cart")

    subtotal = sum((detail.total for detail in order.details.all()), Decimal("0"))
    known_fees = (order.shipping_fee or Decimal("0")) + (order.tax_amount or Decimal("0"))
    other_fee = order.total_amount - subtotal - known_fees
    if other_fee < 0:
        other_fee = Decimal("0")

    return render(
        request,
        "orders/order_confirmation.html",
        {
            "order": order,
            "order_subtotal": subtotal,
            "order_other_fee": other_fee,
        },
    )


# =================================== orders_to_be_processed_view ===================================
@login_required
@admin_or_manager_or_staff_required
def orders_to_be_processed_view(request):
    search_query = request.GET.get("search", "")
    orders = Order.objects.select_related("customer").filter(
        status__in=["Pending", "Out for Delivery"]
    ).order_by("created_at")

    # Apply search filter if search query is provided
    if search_query:
        orders = orders.filter(
            Q(customer__first_name__icontains=search_query)
            | Q(customer__last_name__icontains=search_query)
            | Q(id__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(orders, 25)  # Show 25 orders per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    table_title = "Orders to be Processed"

    return render(
        request,
        "orders/orders_to_be_processed.html",
        {"orders": page_obj, "table_title": table_title, "search_query": search_query},
    )


# =================================== customer_order_history_view ===================================
@login_required
def customer_order_history_view(request):
    try:
        customer = request.user.customer
        orders = (
            Order.objects.filter(customer=customer)
            .prefetch_related("details__product", "details__product_volume__volume")
            .order_by("-created_at")
        )
        total_orders = orders.count()
        delivered_orders = orders.filter(status="Delivered").count()
        pending_orders = orders.filter(status__in=["Pending", "Out for Delivery"]).count()

        return render(
            request,
            "orders/order_history.html",
            {
                "orders": orders,
                "customer": customer,
                "total_orders": total_orders,
                "delivered_orders": delivered_orders,
                "pending_orders": pending_orders,
            },
        )

    except ObjectDoesNotExist:
        messages.error(
            request, "You do not have a customer profile associated with your account."
        )
        return redirect("users-home")


# =================================== all_orders_view ===================================


@login_required
@admin_or_manager_or_staff_required
def all_orders_view(request):
    # Get the status filter from the GET request
    status_filter = request.GET.get("status", "")

    # Get the search term from the GET request
    search_query = request.GET.get("search", "")

    # Filter orders based on status and search term
    if status_filter == "All" or status_filter == "":
        orders = Order.objects.select_related("customer").all()
    else:
        orders = Order.objects.select_related("customer").filter(status=status_filter)

    if search_query:
        orders = orders.filter(
            Q(customer__first_name__icontains=search_query)
            | Q(customer__last_name__icontains=search_query)
            | Q(id__icontains=search_query)
        )

    # Paginate orders (25 orders per page)
    paginator = Paginator(orders, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Context with paginated orders and filters
    context = {
        "orders": page_obj,
        "status_filter": status_filter,
        "search_query": search_query,
    }

    return render(request, "orders/all_orders.html", context)


# =================================== order_report_view ===================================
@login_required
@admin_or_manager_or_staff_required
def order_report_view(request, order_id):
    # Fetch order with its details, and prefetch related volumes through ProductVolume
    order = get_object_or_404(
        Order.objects.select_related("customer").prefetch_related(
            "details__product",
            "details__product_volume__volume",
        ),
        id=order_id,
    )

    return render(request, "orders/order_report.html", {"order": order})


# =================================== order_detail_view ===================================


@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("customer").prefetch_related(
            "details__product",
            "details__product__category",
            "details__product_volume__volume",
        ),
        id=order_id,
        customer=request.user.customer,
    )

    statuses = ["Pending", "Out for Delivery", "Delivered"]
    current_status_index = statuses.index(order.status) if order.status in statuses else -1

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
            "statuses": statuses,
            "current_status_index": current_status_index,
        },
    )


# =================================== order_process_view ===================================
@login_required
@admin_or_manager_or_staff_required
def order_process_view(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("customer").prefetch_related("details"), id=order_id
    )

    if request.method == "POST":
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            order_status = form.cleaned_data[
                "status"
            ]  # Assuming 'status' is the field in the form
            form.save()
            messages.success(
                request, "Order status updated successfully!", extra_tags="bg-success"
            )

            # Send email to the customer
            if order.customer:  # Assuming `order.customer` is the customer's email
                send_order_status_email(
                    recipient_name=order.customer.first_name,
                    recipient_email=order.customer.email,
                    order_status=order_status,
                )

            return redirect("orders:orders_to_be_processed")
        else:
            # Extract error messages
            error_messages = [
                f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()
            ]
            formatted_errors = " ".join(error_messages)
            messages.error(
                request,
                f"Failed to update order status: {formatted_errors}",
                extra_tags="bg-danger",
            )

    else:
        form = OrderStatusForm(instance=order)

    return render(request, "orders/order_process.html", {"order": order, "form": form})


# Send email to customer when the order changes
def send_order_status_email(recipient_name, recipient_email, order_status):
    # Send a stylish email to the customer when their order status is updated.
    subject = f"Your Order Status Has Been Updated: {order_status}"

    # Link to the order history
    order_history_url = "https://jobellinc.com/orders/order-history/"

    # Stylish HTML email body
    email_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
            <h2 style="color: #2E86C1; text-align: center;">Your Order Status Has Been Updated</h2>
            <p>Hi <strong>{recipient_name}</strong>,</p>
            <p>We wanted to let you know that the status of your order has been updated. Your current order status is: <strong>{order_status}</strong>.</p>
            <p>We are committed to keeping you informed throughout the process. If you have any questions or need further assistance regarding your order, please don't hesitate to reach out to us.</p>
            
            <div style="text-align: center; margin: 20px 0;">
                <a href="{order_history_url}" style="background-color: #2E86C1; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px;">View Order History</a>
            </div>

            <p>In the meantime, feel free to explore our latest products:</p>
            <div style="text-align: center; margin: 20px 0;">
                <a href="https://jobellinc.com/" style="background-color: #C0392B; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px;">View Products</a>
            </div>

            <p>Thank you for choosing us, and we look forward to serving you again soon!</p>
            <p style="color: #888;">Warm regards,<br>The Jobel Inc. Team<br>Customer Support</p>
        </div>
    </body>
    </html>
    """

    from_email = getattr(settings, "EMAIL_HOST_USER", None)
    recipient_list = [recipient_email]

    # Send the HTML email
    try:
        send_mail(subject, "", from_email, recipient_list, html_message=email_body)
        logger.info(f"Email sent to {recipient_email}")
    except Exception as e:
        logger.error(f"Error sending email to {recipient_email}: {str(e)}")


# =================================== Sale delete view ===================================
@login_required
@admin_required
@transaction.atomic
def order_delete_view(request, order_id):
    try:
        # Get the order to delete
        order = Order.objects.get(id=order_id)
        order.delete()
        messages.success(
            request, f"Order: {order_id} deleted successfully!", extra_tags="bg-success"
        )
    except Order.DoesNotExist:
        # Specific exception for when the Order is not found
        messages.error(
            request,
            f"Order: {order_id} not found!",
            extra_tags="bg-danger",
        )
    except Exception:
        # General exception for any other errors
        logger.exception("Error deleting order %s", order_id)
        messages.error(
            request,
            "There was an error during the elimination!",
            extra_tags="bg-danger",
        )
    finally:
        return redirect("orders:orders_to_be_processed")
