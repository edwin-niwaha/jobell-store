from django.core.mail import EmailMultiAlternatives
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
from django.contrib import messages
import requests
import uuid
from django.http import JsonResponse, HttpResponse
import logging
import base64
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from .models import Cart, CartItem, Order, OrderDetail, Wishlist
from apps.products.models import Product, ProductVolume, ProductImage
from django.core.exceptions import MultipleObjectsReturned
from .forms import CheckoutForm, OrderStatusForm
from apps.customers.models import Customer
from apps.products.models import Review

from apps.authentication.decorators import (
    admin_required,
    admin_or_manager_or_staff_required,
)


logger = logging.getLogger(__name__)


# =================================== Products Detail ===================================

@login_required
def product_detail(request, id):
    product = get_object_or_404(Product, id=id)

    # Handle review submission
    if request.method == 'POST' and 'submit_review' in request.POST:
        if Review.objects.filter(product=product, user=request.user).exists():
            # Add message for already reviewed
            messages.info(request, "Oops! You've already reviewed this product.", extra_tags="bg-danger")
            return redirect('orders:product_detail', id=id)
        
        review_text = request.POST.get('review_text')
        rating = int(request.POST.get('rating'))

        if review_text and rating:
            Review.objects.create(
                product=product,
                user=request.user,
                review_text=review_text,
                rating=rating
            )

        # Redirect to prevent re-posting the form if refreshed
        return redirect('orders:product_detail', id=id)

    # Handle "Set as Featured" or "Remove from Featured" based on the POST request
    if request.method == 'POST':
        # Check if we are toggling 'is_featured'
        if 'set_featured' in request.POST:
            product.is_featured = True
        elif 'remove_featured' in request.POST:
            product.is_featured = False
        
        # Save the updated product
        product.save()
        return redirect('orders:product_detail', id=id)

    # Continue fetching cart and product details
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    cart_count = sum(item.quantity for item in cart_items)

    # Fetch volumes specific to this product
    product_volumes = ProductVolume.objects.filter(product=product).order_by("volume__ml")

    # Fetch reviews
    reviews = Review.objects.filter(product=product, is_verified=True).order_by('-created_at')

    # Pagination
    paginator = Paginator(reviews, 5)  # Show 5 reviews per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Count of verified reviews (assuming there is an 'is_verified' field in your Review model)
    verified_reviews_count = reviews.filter(is_verified=True).count()

    # Process reviews to generate the filled and empty stars
    for review in page_obj:
        review.filled_stars = '★' * review.rating
        review.empty_stars = '☆' * (5 - review.rating)

    context = {
        "product": product,
        "product_volumes": product_volumes,
        "cart_count": cart_count,
        "reviews": page_obj,  # Pass paginated reviews
        "verified_reviews_count": verified_reviews_count,  # Add verified reviews count
    }

    return render(request, "orders/product_detail.html", context)

# =================================== Products Detail for quests not signed in ===================================


def product_details_view(request, id):
    try:
        # Fetch the product and related ProductVolume details
        product = Product.objects.get(id=id)
        product_volumes = ProductVolume.objects.filter(product=product).order_by(
            "volume__ml"
        )

        # Prepare context with product and volume details
        context = {
            "product_id": product.id,
            "name": product.name,
            "gender": product.gender,
            "description": product.description,
            "category": product.category.name if product.category else "N/A",
            "volumes": [],
        }

        # Loop through ProductVolume instances to gather the volume details
        for product_volume in product_volumes:
            volume = product_volume.volume  # Get the related Volume object
            discount_value = product_volume.discount_value or 0
            volume_data = {
                "ml": volume.ml,
                "price": volume.price,
                "image": volume.image.url if volume.image else "",
                "product_type": product_volume.product_type,  # Include the product type if needed
                "discount_value": discount_value,
                "discounted_price": product_volume.get_discounted_price(),  # Apply any discount
            }
            context["volumes"].append(volume_data)

        return render(request, "orders/product_detail_partial.html", context)
    except Product.DoesNotExist:
        return render(
            request,
            "orders/product_detail_partial.html",
            {"error": "Product not found"},
        )


# =================================== Products Wishlist ===================================
@login_required
def wishlist_add(request, product_id):
    # Get the product object
    product = get_object_or_404(Product, id=product_id)

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

    # Redirect back to the product detail page
    return redirect("orders:product_detail", id=product.id)


# =================================== wishlist_view ===================================
@login_required
def wishlist_view(request):
    # Fetch all the products in the user's wishlist
    wishlist_items = Wishlist.objects.filter(user=request.user)

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

    # Pass the page object to the template
    context = {"page_obj": page_obj}
    return render(request, "orders/wishlist.html", context)


# =================================== remove_from_wishlist ===================================


@login_required
def remove_from_wishlist(request, wishlist_item_id):
    # Log the wishlist item ID to ensure it's being passed correctly
    print(f"Wishlist Item ID passed: {wishlist_item_id}")

    try:
        # Check if the wishlist item exists for the logged-in user
        wishlist_item = Wishlist.objects.get(id=wishlist_item_id, user=request.user)
        print(f"Wishlist item found: {wishlist_item.product.name}")
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
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    quantity = int(request.POST.get("quantity", 1))
    volume_id = request.POST.get("volume_id")

    # Validate the volume
    if not volume_id:
        messages.error(request, "Please select a product volume.")
        return redirect("orders:product_detail", id=product_id)

    # Fetch the selected volume
    volume = get_object_or_404(ProductVolume, id=volume_id)

    if quantity <= 0:
        messages.add_message(
            request,
            messages.ERROR,
            "Invalid quantity. It must be greater than zero.",
            extra_tags="bg-danger text-white",
        )
        return redirect("orders:product_detail", id=product_id)

    try:
        # Add volume to the CartItem creation or retrieval
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, volume=volume
        )
    except MultipleObjectsReturned:
        cart_item = CartItem.objects.filter(
            cart=cart, product=product, volume=volume
        ).first()

    if not created:
        cart_item.quantity += quantity
        cart_item.save()
        messages.add_message(
            request,
            messages.INFO,
            f"Increased quantity of {product.name} ({volume.volume.ml} ML) to {cart_item.quantity} in your cart.",
            extra_tags="bg-info text-white",
        )
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.add_message(
            request,
            messages.SUCCESS,
            f"{product.name} ({volume.volume.ml} ML) has been added to your cart with quantity {quantity}.",
            extra_tags="bg-success text-white",
        )

    return redirect("orders:product_detail", id=product_id)


# =================================== cart_view ===================================
@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)

    total_price = sum(item.get_total_price() for item in cart.items.all())

    context = {
        "cart": cart,
        "total_price": total_price,
    }

    return render(request, "orders/cart.html", context)


@login_required
def update_cart(request, item_id):
    cart = get_object_or_404(Cart, user=request.user)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)

    if request.method == "POST":
        quantity = int(request.POST.get("quantity", 1))

        if quantity > 0:
            item.quantity = quantity
            item.save()
            messages.success(
                request, "Cart updated successfully.", extra_tags="bg-success"
            )
        else:
            messages.error(
                request, "Quantity must be at least 1.", extra_tags="bg-danger"
            )

    return redirect("orders:cart")


@login_required
def remove_from_cart(request, item_id):
    cart = get_object_or_404(Cart, user=request.user)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)

    item.delete()
    messages.success(request, "Item removed from cart.", extra_tags="bg-success")

    return redirect("orders:cart")



def send_order_email(
    recipient_name,
    recipient_email,
    order_id,
    order_details,
    order_status,
    total_price,
    is_customer=True,
):
    customer_order_history_url = "https://jobellinc.com/orders/order-history/"
    orders_to_be_processed_url = "https://jobellinc.com/orders/to-be-processed/"
    subject = "Your Order has been Placed" if is_customer else "New Order to Process"

    if is_customer:
        email_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px; background-color: #f9f9f9;">
                    <h2 style="color: #2E86C1; text-align: center;">Thank You for Your Purchase!</h2>
                    <p>Dear <strong>{recipient_name}</strong>,</p>
                    <p>Thank you for placing your order with us! We appreciate your trust in our products and services. Your order has been successfully received and is being processed. Here are the details of your order:</p>

                    <h4>Order ID: <strong>{order_id}</strong> | Status: <span style="color: #FF5733;">{order_status}</span></h4>
                    
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                        <tr style="background-color: #f2f2f2;">
                            <th style="padding: 10px; border: 1px solid #ddd;">Product</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">Volume</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">Qty</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">Price @</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">Image</th>
                        </tr>
                        {''.join(
                            f"""
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;">{item['product_name']}</td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{item['volume']} ML</td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{item['quantity']}</td>
                                <td style="padding: 10px; border: 1px solid #ddd;">UgX {item['price']:,.2f}</td>
                                <td style="padding: 10px; border: 1px solid #ddd;">
                                    <img src="{item['image_url']}" alt="{item['product_name']}" style="width: 50px; height: auto; border-radius: 5px;">
                                </td>
                            </tr>
                            """ for item in order_details
                        )}
                    </table>

                    <h3 style="text-align: right; color: #2E86C1;">Total Price: UgX {total_price:,.2f}</h3>

                    <div style="text-align: center; margin: 20px 0;">
                        <a href="{customer_order_history_url}" style="background-color: #2E86C1; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px;">View Order History</a>
                    </div>

                    <p>Thank you for shopping with us!</p>
                    <p style="color: #888;">- Jobel Inc Management</p>
                </div>
            </body>
        </html>

        """
    else:
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #C0392B; text-align: center;">New Order to Process</h2>
                <p>Hello <strong>Jobel Inc Team</strong>,</p>
                <p>A new order has been placed. The order ID is <strong>{order_id}</strong>. Please review and process the order by clicking the button below:</p>
                <div style="text-align: center; margin: 20px 0;">
                    <a href="{orders_to_be_processed_url}" style="background-color: #C0392B; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px;">Process Order</a>
                </div>
                <p>Thanks for your prompt attention!</p>
                <p style="color: #888;">- Jobel Inc Management</p>
            </div>
        </body>
        </html>
        """

    from_email = getattr(settings, "EMAIL_HOST_USER", None)
    to = [recipient_email]

    # Send HTML email
    try:
        email = EmailMultiAlternatives(subject, strip_tags(email_body), from_email, to)
        email.attach_alternative(email_body, "text/html")
        email.send()
        return True
    except Exception as e:
        logger.error(f"Error sending email to {recipient_email}: {str(e)}")
        return False



@login_required
def checkout_view(request):
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        messages.error(request, "Your cart is empty.")
        return redirect("orders:cart")  # Redirect to cart view if the cart is empty

    customer, created = Customer.objects.get_or_create(user=request.user)

    total_price = sum(
        item.get_total_price() for item in cart.items.all()
    )  # Calculate total price

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            total_amount = total_price  # Use total_price here

            # Update customer details
            customer.first_name = form.cleaned_data["first_name"]
            customer.last_name = form.cleaned_data["last_name"]
            customer.email = form.cleaned_data["email"]
            customer.mobile = form.cleaned_data["mobile"]
            customer.address = form.cleaned_data["address"]
            customer.save()

            # Create the order
            order = Order.objects.create(
                customer=customer,
                created_at=timezone.now(),
                total_amount=total_amount,
                status="Pending",
            )

            order_details = []  # Initialize order_details list

            # Create OrderDetail entries
            for item in cart.items.all():
                product_volume = item.volume
                discounted_price = product_volume.get_discounted_price()
                image_url = (
                    product_volume.volume.image.url
                    if product_volume.volume.image
                    else ""
                )

                order_details.append(
                    {
                        "product_name": item.product.name,
                        "volume": item.volume.volume.ml,
                        "quantity": item.quantity,
                        "price": discounted_price,
                        "image_url": image_url,
                        "order_status": order.status,
                    }
                )

                OrderDetail.objects.create(
                    order=order,
                    product=item.product,
                    product_volume=item.volume,
                    quantity=item.quantity,
                    discounted_price=discounted_price,
                    price=item.volume.volume.price,
                )

            # Clear cart after checkout
            cart.items.all().delete()

            # Send confirmation emails
            send_order_email(
                customer.first_name,
                customer.email,
                order.id,
                order_details,
                order.status,
                total_price,
                is_customer=True,
            )
            send_order_email(
                "Jobel Inc",
                settings.EMAIL_HOST_USER,
                order.id,
                order_details,
                order.status,
                total_price,
                is_customer=False,
            )

            messages.success(
                request,
                f"Your order has been placed successfully! Order ID: {order.id}",
            )
            return redirect("orders:order_confirmation", order_id=order.id)

    else:
        form = CheckoutForm(
            initial={
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "email": customer.email,
                "mobile": customer.mobile,
                "address": customer.address,
            }
        )

    return render(
        request,
        "orders/checkout.html",
        {"form": form, "cart": cart, "total_price": total_price},
    )


# =================================== process_payment ===================================
@login_required
def process_payment(request, order_id):
    """
    Handles the payment processing for a given order.
    """
    order = get_object_or_404(Order, id=order_id)
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
    order = get_object_or_404(Order, id=order_id)
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
def payment_flutter_view(request):
    unique_tx_ref = f"txref-{uuid.uuid4()}"  # Generate a unique transaction reference
    context = {
        "unique_tx_ref": unique_tx_ref,
        "public_key": "FLWPUBK_TEST-02b9b5fc6406bd4a41c3ff141cc45e93-X",
        "currency": "UGX",
        "form_title": "Secure Flutterwave Payment",
    }
    return render(request, "orders/payment_flutter.html", context)


# =================================== order_confirmation_view ===================================
@login_required
def order_confirmation_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "orders/order_confirmation.html", {"order": order})


# =================================== orders_to_be_processed_view ===================================
@login_required
@admin_or_manager_or_staff_required
def orders_to_be_processed_view(request):
    search_query = request.GET.get("search", "")
    orders = Order.objects.filter(status__in=["Pending", "Out for Delivery"]).order_by(
        "created_at"
    )

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
        orders = Order.objects.filter(customer=customer).order_by("-created_at")

        return render(
            request,
            "orders/order_history.html",
            {"orders": orders, "customer": customer},
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
        orders = Order.objects.all()
    else:
        orders = Order.objects.filter(status=status_filter)

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
def order_report_view(request, order_id):
    # Fetch order with its details, and prefetch related volumes through ProductVolume
    order = get_object_or_404(
        Order.objects.prefetch_related(
            "details__product__volumes",  # Prefetch volumes related to products in the order
        ),
        id=order_id,
    )

    print("Order Details Count:", order.details.count())

    # Printing product names, quantities, prices, and volume details for debugging
    for detail in order.details.all():
        print(detail.product.name, detail.quantity, detail.price)

        # Fetch the first associated volume for each product (or logic for selecting one volume)
        product_volumes = detail.product.volumes.all()
        if product_volumes:
            volume = product_volumes[
                0
            ]  # Assuming we take the first volume if available
            print("Volume ML:", volume.ml)  # Print the volume in ML

    return render(request, "orders/order_report.html", {"order": order})


# =================================== order_detail_view ===================================


@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user.customer)

    statuses = ["Pending", "Out for Delivery", "Delivered"]
    total_statuses = len(statuses)
    progress_width = (
        100 / total_statuses if total_statuses else 0
    )  # Calculate the width for each status

    return render(
        request,
        "orders/order_detail.html",
        {"order": order, "statuses": statuses, "progress_width": progress_width},
    )


# =================================== order_process_view ===================================
@login_required
@admin_or_manager_or_staff_required
@login_required
@admin_or_manager_or_staff_required
def order_process_view(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related("details"), id=order_id)

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
    except Exception as e:
        # General exception for any other errors
        messages.error(
            request,
            "There was an error during the elimination!",
            extra_tags="bg-danger",
        )
        print(e)
    finally:
        return redirect("orders:orders_to_be_processed")
