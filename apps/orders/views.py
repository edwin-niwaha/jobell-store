from django.core.mail import EmailMultiAlternatives
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.core.paginator import Paginator
from django.db.models import Q
from django.conf import settings
from django.contrib import messages
import requests
import uuid
from django.http import JsonResponse
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

from apps.authentication.decorators import (
    admin_required,
    admin_or_manager_or_staff_required,
)


logger = logging.getLogger(__name__)


# =================================== Products Detail ===================================
@login_required
def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    cart_count = sum(item.quantity for item in cart_items)

    # Fetch volumes specific to this product
    product_volumes = ProductVolume.objects.filter(product=product)

    context = {
        "product": product,
        "product_volumes": product_volumes,  # Pass product-specific volumes to the template
        "cart_count": cart_count,
    }

    return render(request, "orders/product_detail.html", context)


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
def remove_from_wishlist(request, product_id):
    # Get the wishlist item to remove
    wishlist_item = get_object_or_404(
        Wishlist, user=request.user, product_id=product_id
    )

    # Remove the item from the wishlist
    wishlist_item.delete()

    # Redirect back to the wishlist view
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


# =================================== checkout_view ===================================
def send_order_email(recipient_name, recipient_email, order_id, is_customer=True):

    customer_order_history_url = "https://jobellinc.com/api/orders/order-history/"
    orders_to_be_processed_url = "https://jobellinc.com/api/orders/to-be-processed/"
    subject = "Your Order has been Placed" if is_customer else "New Order to Process"

    if is_customer:
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #2E86C1; text-align: center;">Thank You for Your Purchase!</h2>
                <p>Hello <strong>{recipient_name}</strong>,</p>
                <p>Your order ID is <strong>{order_id}</strong>. You can view your order details and track the status by clicking the button below:</p>
                <div style="text-align: center; margin: 20px 0;">
                    <a href="{customer_order_history_url}" style="background-color: #2E86C1; color: #fff; text-decoration: none; padding: 10px 20px; border-radius: 5px;">View Order History</a>
                </div>
                <p>Thanks for shopping with us!</p>
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
        return redirect(
            "orders:cart_view"
        )  # Redirect to cart view if the cart is empty

    # Get or create a customer entry for the current user
    customer, created = Customer.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            total_amount = cart.get_total_price()

            # Update the customer's information from the form
            customer.first_name = form.cleaned_data["first_name"]
            customer.last_name = form.cleaned_data["last_name"]
            customer.email = form.cleaned_data["email"]
            customer.phone = form.cleaned_data["phone"]
            customer.address = form.cleaned_data["address"]
            customer.save()  # Save the updated customer information

            # Create the order
            order = Order.objects.create(
                customer=customer,
                created_at=timezone.now(),
                total_amount=total_amount,
                status="Pending",  # Or set a default status
            )

            # Create OrderDetail entries for each item in the cart
            for item in cart.items.all():
                # item.volume refers to the ProductVolume
                OrderDetail.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.volume.price,  # Use price from ProductVolume
                )

            # Clear the cart items after checkout
            cart.items.all().delete()

            # Send email to customer and retail (both using the same sender email)
            send_order_email(
                customer.first_name, customer.email, order.id, is_customer=True
            )
            send_order_email(
                "Jobell Inc", settings.EMAIL_HOST_USER, order.id, is_customer=False
            )

            # Optionally, redirect to an order confirmation page
            messages.success(
                request,
                f"Your order has been placed successfully! Order ID: {order.id}",
            )
            return redirect("orders:order_confirmation", order_id=order.id)

    else:
        # Prepopulate the form with existing customer data if available
        form = CheckoutForm(
            initial={
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "email": customer.email,
                "phone": customer.phone,
                "address": customer.address,
            }
        )

    return render(request, "orders/checkout.html", {"form": form, "cart": cart})


# =================================== process_payment ===================================
@login_required
def process_payment(request, order_id):
    """
    Handles the payment processing for a given order.
    """
    order = get_object_or_404(Order, id=order_id)
    form_title = "Payment Details"

    # Retrieve the customer's phone number
    phone_number = order.customer.phone
    if not phone_number:
        return JsonResponse(
            {"error": "The customer does not have a valid phone number."}, status=400
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
    orders = Order.objects.filter(status__in=["Pending", "Shipped"]).order_by(
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
# @login_required
# @admin_or_manager_or_staff_required
# def all_orders_view(request):
#     status_filter = request.GET.get("status", "")
#     if status_filter == "All" or status_filter == "":
#         orders = Order.objects.all().order_by("-created_at")
#     else:
#         orders = Order.objects.filter(status=status_filter)

#     context = {
#         "orders": orders,
#         "status_filter": status_filter,
#     }
#     return render(request, "orders/all_orders.html", context)


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
    return render(request, "orders/order_detail.html", {"order": order})


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
    order_history_url = "https://jobellinc.com/api/orders/order-history/"

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
