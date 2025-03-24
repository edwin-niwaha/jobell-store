import json
import logging
from decimal import Decimal
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models import Sum, Count
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from core.wsgi import *
from xhtml2pdf import pisa
from django.template.loader import get_template
from apps.customers.models import Customer
from apps.inventory.models import Inventory
from apps.products.models import Product, ProductVolume
from .models import Sale, SaleDetail
from .forms import ReportPeriodForm


# Import custom decorators
from apps.authentication.decorators import (
    admin_or_manager_or_staff_required,
    admin_required,
)

logger = logging.getLogger(__name__)


# =================================== Sale list view ===================================
@login_required
@admin_or_manager_or_staff_required
def sales_list_view(request):
    # Get the search term from the GET request
    search_query = request.GET.get("search", "")

    # Filter sales based on search term (e.g., customer name or sale ID)
    if search_query:
        sales = (
            Sale.objects.filter(
                Q(customer__first_name__icontains=search_query)
                | Q(customer__last_name__icontains=search_query)
                | Q(id__icontains=search_query)
            )
            .select_related("customer")
            .prefetch_related("items__product__productvolume_set__volume")
            .order_by("id")
        )
    else:
        sales = (
            Sale.objects.all()
            .select_related("customer")
            .prefetch_related("items__product__productvolume_set__volume")
            .order_by("id")
        )

    # Paginate the sales (10 sales per page)
    paginator = Paginator(sales, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calculate grand total and total items
    grand_total = sales.aggregate(Sum("grand_total"))["grand_total__sum"] or 0
    total_items = sum(
        sale.sum_items() for sale in sales
    )  # Assuming sum_items() method is defined

    # Context with paginated sales and other variables
    context = {
        "table_title": "sales",
        "sales": page_obj,
        "grand_total": grand_total,
        "total_items": total_items,
        "search_query": search_query,  # Include search query for the search form
    }

    return render(request, "sales/sales.html", context=context)


# =================================== sales_report_view view ===================================


# @admin_or_manager_or_staff_required
# @login_required
# def sales_report_view(request):
#     # Initialize the form with GET data
#     form = ReportPeriodForm(request.GET)
#     start_date = None
#     end_date = None

#     if form.is_valid():
#         start_date = form.cleaned_data["start_date"]
#         end_date = form.cleaned_data["end_date"]

#     # Filter sales by date range and prefetch related data
#     sales = Sale.objects.filter(
#         trans_date__range=[start_date, end_date]
#     ).prefetch_related("items__product_volume__volume", "items__product")

#     # Aggregate totals
#     total_sales = sales.aggregate(
#         total_revenue=Sum("items__total_detail"),  # Calculate directly from items
#         total_items_sold=Sum("items__quantity"),
#         total_transactions=Count("id"),
#     )

#     # Calculate COGS
#     cogs = 0
#     for sale in sales:
#         for item in sale.items.all():
#             product_volume = item.product_volume
#             if product_volume and product_volume.volume:
#                 cogs += product_volume.volume.cost * item.quantity

#     # Calculate stock balance
#     stock_balance = (
#         Inventory.objects.aggregate(total_stock=Sum("quantity"))["total_stock"] or 0
#     )

#     # Prepare detailed sales data
#     sale_details = []
#     total_profit_after_sales = 0

#     for sale in sales:
#         sale_profit = 0
#         item_details = []

#         for item in sale.items.all():
#             product = item.product
#             product_volume = item.product_volume

#             if product_volume and product_volume.volume:
#                 volume = product_volume.volume
#                 # Apply discount if exists
#                 discounted_price = product_volume.get_discounted_price()
#                 item_profit = (discounted_price - volume.cost) * item.quantity
#                 sale_profit += item_profit
#                 total_profit_after_sales += item_profit

#                 item_details.append(
#                     {
#                         "product": product.name,
#                         "volume": volume.ml,
#                         "price": discounted_price,  # Use discounted price
#                         "cost": volume.cost,
#                         "quantity": item.quantity,
#                         "total": item.total_detail,
#                     }
#                 )

#         sale_details.append(
#             {
#                 "trans_date": sale.trans_date,
#                 "customer": (
#                     f"{sale.customer.first_name} {sale.customer.last_name}"
#                     if sale.customer
#                     else "N/A"
#                 ),
#                 "grand_total": sale.grand_total,
#                 "profit": sale_profit,
#                 "payment_method": sale.payment_method,
#                 "item_details": item_details,
#             }
#         )

#     context = {
#         "form": form,
#         "start_date": start_date,
#         "end_date": end_date,
#         "total_revenue": total_sales["total_revenue"],
#         "total_items_sold": total_sales["total_items_sold"],
#         "total_transactions": total_sales["total_transactions"],
#         "total_cogs": cogs,
#         "sales": sale_details,
#         "stock_balance": stock_balance,
#         "total_profit_after_sales": total_profit_after_sales,
#         "table_title": "Sales Report",
#     }

#     return render(request, "sales/sales_report.html", context)


def sales_report_view(request):
    # Initialize the form with GET data
    form = ReportPeriodForm(request.GET)
    start_date = None
    end_date = None

    if form.is_valid():
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]

    # Filter sales by date range and prefetch related data
    sales = Sale.objects.filter(
        trans_date__range=[start_date, end_date]
    ).prefetch_related("items__product_volume__volume", "items__product")

    # Aggregate totals
    total_sales = sales.aggregate(
        total_revenue=Sum("items__total_detail"),  # Calculate directly from items
        total_items_sold=Sum("items__quantity"),
        total_transactions=Count("id"),
    )

    cogs = 0
    for sale in sales:
        for item in sale.items.all():
            product_volume = item.product_volume
            if product_volume and product_volume.volume:
                cogs += product_volume.volume.cost * item.quantity

    # Calculate stock balance
    stock_balance = (
        Inventory.objects.aggregate(total_stock=Sum("quantity"))["total_stock"] or 0
    )

    # Prepare detailed sales data
    sale_details = []
    total_profit_after_sales = 0

    for sale in sales:
        sale_profit = 0
        item_details = []

        for item in sale.items.all():
            product = item.product
            product_volume = item.product_volume
            # Get the original price from the ProductVolume (before discount)
            original_price = (
                product_volume.volume.price if product_volume else product.price
            )

            # Apply discount if exists (use price from SaleDetail)
            discounted_price = item.price  # Use the price from SaleDetail directly
            item_profit = (
                (Decimal(discounted_price) - product_volume.volume.cost) * item.quantity
                if product_volume
                else 0
            )
            sale_profit += item_profit
            total_profit_after_sales += item_profit

            item_details.append(
                {
                    "product": product.name,
                    "volume": product_volume.volume.ml if product_volume else None,
                    "original_price": original_price,  # Add original price
                    "price": discounted_price,  # Use price from SaleDetail
                    "cost": (
                        product_volume.volume.cost if product_volume else 0
                    ),  # Use cost from ProductVolume
                    "quantity": item.quantity,
                    "total": item.total_detail,
                }
            )

        sale_details.append(
            {
                "trans_date": sale.trans_date,
                "customer": (
                    f"{sale.customer.first_name} {sale.customer.last_name}"
                    if sale.customer
                    else "N/A"
                ),
                "grand_total": sale.grand_total,
                "profit": sale_profit,
                "payment_method": sale.payment_method,
                "item_details": item_details,
            }
        )

    context = {
        "form": form,
        "start_date": start_date,
        "end_date": end_date,
        "total_revenue": total_sales["total_revenue"],
        "total_items_sold": total_sales["total_items_sold"],
        "total_transactions": total_sales["total_transactions"],
        "total_cogs": cogs,
        "sales": sale_details,
        "stock_balance": stock_balance,
        "total_profit_after_sales": total_profit_after_sales,
        "table_title": "Sales Report",
    }

    return render(request, "sales/sales_report.html", context)


# =================================== Sale Add view ===================================
@admin_or_manager_or_staff_required
@login_required
def sales_add_view(request):
    # Fetch products with active status and related inventory and volumes
    products = (
        Product.objects.filter(status="ACTIVE")
        .select_related("inventory")
        .prefetch_related("productvolume_set__volume")  # Include volume relation
    )

    # Prepare context for rendering
    context = {
        "customers": [c.to_select2() for c in Customer.objects.all()],
        "products": products,
        "total_stock": sum(
            product.inventory.quantity if hasattr(product, "inventory") else 0
            for product in products
        ),
    }

    if request.method == "POST":
        try:
            logger.debug(f"POST data: {request.POST}")

            # Extract and process form data
            customer_id = int(request.POST.get("customer"))
            sale_attributes = {
                "customer": Customer.objects.get(id=customer_id),
                "trans_date": request.POST.get("trans_date"),
                "sub_total": float(request.POST.get("sub_total", 0)),
                "grand_total": float(request.POST.get("grand_total", 0)),
                "tax_amount": float(request.POST.get("tax_amount", 0)),
                "tax_percentage": float(request.POST.get("tax_percentage", 0)),
                "amount_payed": float(request.POST.get("amount_payed", 0)),
                "amount_change": float(request.POST.get("amount_change", 0)),
            }

            with transaction.atomic():
                # Create the sale
                new_sale = Sale.objects.create(**sale_attributes)
                logger.info(f"Sale created successfully: {sale_attributes}")

                # Extract product details from form data
                products_data = request.POST.getlist("products")
                for product_data_str in products_data:
                    product_data = json.loads(product_data_str)

                    # Parse combined product and volume IDs
                    product_id, volume_id = map(int, product_data["id"].split("-"))
                    product_obj = Product.objects.get(id=product_id)
                    product_volume = ProductVolume.objects.select_related("volume").get(
                        id=volume_id
                    )

                    # Fetch price and discount
                    original_price = product_volume.volume.price
                    discounted_price = (
                        product_volume.get_discounted_price()
                    )  # Apply discount if any

                    quantity_requested = int(product_data["quantity"])

                    # Check if the product's inventory has sufficient stock
                    if (
                        not hasattr(product_obj, "inventory")
                        or product_obj.inventory.quantity < quantity_requested
                    ):
                        raise ValueError(
                            f"Oops! Insufficient stock for {product_obj.name}"
                        )

                    # Update inventory stock at the product level
                    inventory_obj = product_obj.inventory
                    inventory_obj.quantity -= quantity_requested
                    inventory_obj.save()
                    logger.info(
                        f"Stock updated for {product_obj.name}: {inventory_obj.quantity}"
                    )

                    # Create sale detail
                    detail_attributes = {
                        "sale": new_sale,
                        "product": product_obj,
                        "product_volume": product_volume,
                        "price": discounted_price,  # Use discounted price
                        "quantity": quantity_requested,
                        "total_detail": discounted_price
                        * quantity_requested,  # Apply discount in total
                    }
                    SaleDetail.objects.create(**detail_attributes)
                    logger.info(f"Sale detail added: {detail_attributes}")

                # Success message
                messages.success(
                    request, "Sale created successfully!", extra_tags="bg-success"
                )
                return redirect("sales:sales_add")

        except ValueError as ve:
            logger.error(f"Stock error: {ve}")
            messages.error(request, str(ve), extra_tags="bg-danger")
        except Exception as e:
            logger.error(f"Error during sale creation: {e}")
            messages.error(
                request,
                f"There was an error during the creation! Error: {e}",
                extra_tags="bg-danger",
            )

        return redirect("sales:sales_add")

    return render(request, "sales/sales_add.html", context=context)


# =================================== Sale details view ===================================
@login_required
@admin_or_manager_or_staff_required
def sales_details_view(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)

    # Get the sale details related to the sale
    details = SaleDetail.objects.filter(sale=sale)

    context = {
        "active_icon": "sales",
        "sale": sale,
        "details": details,
    }

    return render(request, "sales/sales_details.html", context=context)


# =================================== Sale delete view ===================================
@login_required
@admin_required
@transaction.atomic
def sale_delete_view(request, sale_id):
    try:
        # Get the sale to delete
        sale = Sale.objects.get(id=sale_id)
        sale.delete()
        messages.success(
            request, f"Sale: {sale_id} deleted successfully!", extra_tags="bg-success"
        )
    except Sale.DoesNotExist:
        # Specific exception for when the sale is not found
        messages.error(
            request,
            f"Sale: {sale_id} not found!",
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
        return redirect("sales:sales_list")


# =================================== Sale receipt view ===================================
@login_required
@admin_or_manager_or_staff_required
def receipt_pdf_view(request, sale_id):
    # Get the sale
    sale = Sale.objects.get(id=sale_id)

    # Get the sale details
    details = SaleDetail.objects.filter(sale=sale)

    # Render the template
    template = get_template("sales/sales_receipt_pdf.html")
    context = {"sale": sale, "details": details}
    html_template = template.render(context)

    # Create a file-like buffer to receive PDF data
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="receipt.pdf"'

    # Convert HTML to PDF
    pisa_status = pisa.CreatePDF(html_template, dest=response)

    # Check if PDF was created successfully
    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)

    return response
