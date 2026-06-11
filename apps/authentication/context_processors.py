from apps.authentication.models import Profile, Contact
from apps.products.models import Product
from apps.orders.models import Order, Cart, CartItem
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404


def guest_profiles_context(request):
    # Fetch all profiles with the role "guest"
    guest_profiles = Profile.objects.filter(role="guest")

    # Calculate the number of guest profiles
    guest_count = guest_profiles.count()

    # Return context dictionary
    return {
        "guest_profiles": guest_profiles,
        "guest_count": guest_count,
    }


def guest_user_feedback_context(request):
    # Fetch all invalid feedback entries
    user_feedback = Contact.objects.filter(is_valid=False)

    # Calculate the count of invalid feedback entries
    feedback_count = user_feedback.count()

    # Return context dictionary
    return {
        "user_feedback": user_feedback,
        "feedback_count": feedback_count,
    }


def low_stock_alerts_context(request):
    # Fetch all products along with their inventory
    products = Product.objects.select_related("inventory").all()

    # Filter products with low stock based on inventory
    low_stock_products = products.filter(
        inventory__quantity__lte=F("inventory__low_stock_threshold")
    )

    # Count of low stock products
    low_stock_count = low_stock_products.count()

    return {
        "low_stock_products": low_stock_products,
        "low_stock_count": low_stock_count,
    }


def pending_orders_context(request):
    # Fetch orders that still need fulfilment attention.
    pending_and_out_for_delivery = Order.objects.filter(
        status__in=["Pending", "Processing", "Shipped", "Out for Delivery"]
    ).select_related("customer")

    # Count the total number of pending and Out for Delivery orders
    pending_and_out_for_delivery_count = pending_and_out_for_delivery.count()

    return {
        "pending_and_out_for_delivery": pending_and_out_for_delivery,
        "pending_orders_count": pending_and_out_for_delivery_count,
    }


# def cart_count_user_context(request):
#     cart_count_user = 0

#     if request.user.is_authenticated:
#         cart, _ = Cart.objects.get_or_create(user=request.user)
#         cart_count_user = (
#             CartItem.objects.filter(cart=cart).aggregate(
#                 total_quantity=Sum("quantity")
#             )["total_quantity"]
#             or 0
#         )

#     return {
#         "cart_count_user": cart_count_user,
#     }


# def cart_count_user_context(request):
#     cart_count_user = 0

#     if request.user.is_authenticated:
#         cart, _ = Cart.objects.get_or_create(user=request.user)
#     else:
#         cart_id = request.session.get("cart_id")
#         if cart_id:
#             cart = get_object_or_404(Cart, id=cart_id, user=None)
#         else:
#             cart = None  # No cart for anonymous user yet

#     if cart:
#         cart_count_user = (
#             CartItem.objects.filter(cart=cart).aggregate(
#                 total_quantity=Sum("quantity")
#             )["total_quantity"]
#             or 0
#         )

#     return {
#         "cart_count_user": cart_count_user,
#     }


def cart_count_user_context(request):
    cart_count_user = 0

    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user, session_key=None)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()  # Ensure session exists
            session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
        request.session["session_key"] = session_key
        request.session.modified = True

    if cart:
        cart_count_user = (
            CartItem.objects.filter(cart=cart).aggregate(
                total_quantity=Sum("quantity")
            )["total_quantity"]
            or 0
        )

    return {
        "cart_count_user": cart_count_user,
    }
