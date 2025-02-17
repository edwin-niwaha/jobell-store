from django.shortcuts import render, get_object_or_404, redirect
from django.db import IntegrityError
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Inventory
from .forms import InventoryForm
from apps.inventory.models import Product

from apps.authentication.decorators import (
    admin_or_manager_or_staff_required,
    admin_required,
)


# =================================== Inventory list view ===================================
@login_required
@admin_or_manager_or_staff_required
def inventory_list_view(request):
    search_query = request.GET.get("search", "")
    inventories = Inventory.objects.select_related("product").all()

    # If there's a search query, filter the inventory based on the product name or category
    if search_query:
        inventories = inventories.filter(
            Q(product__name__icontains=search_query)
            | Q(product__category__name__icontains=search_query)
        )

    # Pagination logic
    paginator = Paginator(inventories, 25)  # Show 25 inventories per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "inventories": page_obj,
        "table_title": "Inventory List",
        "search_query": search_query,  # To persist the search query in the search box
    }
    return render(request, "inventory/inventory_list.html", context)


# =================================== Inventory Report view ===================================
@login_required
@admin_or_manager_or_staff_required
def inventory_report_view(request):
    # Search functionality
    search_query = request.GET.get("search", "")
    if search_query:
        inventories = Inventory.objects.filter(
            Q(product__name__icontains=search_query)
            | Q(product__description__icontains=search_query)
        ).select_related("product")
    else:
        inventories = Inventory.objects.select_related("product").all()

    # Pagination
    paginator = Paginator(inventories, 25)  # Show 25 inventories per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calculate total stock from inventory quantities
    total_stock = inventories.aggregate(total_stock=Sum("quantity"))["total_stock"] or 0

    # Prepare context for rendering
    context = {
        "active_icon": "inventory",
        "inventories": page_obj,  # Pass the page object for pagination
        "total_stock": total_stock,
        "table_title": "Inventory Report",
        "search_query": search_query,  # Pass the search query back to the template
    }

    return render(request, "inventory/inventory_report.html", context=context)


# =================================== Inventory Add view ===================================
# @login_required
# @admin_or_manager_or_staff_required
# def inventory_add_view(request):
#     context = {
#         "table_title": "Add Inventory",
#     }
#     if request.method == "POST":
#         form = InventoryForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(
#                 request, "Inventory added successfully!", extra_tags="bg-success"
#             )
#             return redirect(
#                 "inventory:inventory_list"
#             )  # Adjust the redirect as necessary
#     else:
#         form = InventoryForm()
#         context["form"] = form

#     return render(request, "inventory/inventory_add.html", context=context)


@login_required
@admin_or_manager_or_staff_required
def inventory_add_view(request):
    context = {
        "table_title": "Add Inventory",
        "products": Product.objects.filter(
            status="ACTIVE"
        ),  # Pass only active products
    }

    if request.method == "POST":
        form = InventoryForm(request.POST)
        if form.is_valid():
            # Get the product ID from the form data (use `product_id` instead of `product` field)
            product_id = request.POST.get(
                "product_id"
            )  # Assuming the field name is 'product_id'
            product = Product.objects.get(id=product_id)

            # Check if the inventory for this product already exists
            existing_inventory = Inventory.objects.filter(product=product).first()

            if existing_inventory:
                # If an inventory entry for this product already exists, show a message
                messages.error(
                    request,
                    "This product already has an inventory entry!",
                    extra_tags="bg-danger",
                )
                return redirect(
                    "inventory:inventory_list"
                )  # Redirect to inventory list

            # Save the form but don't commit yet
            inventory = form.save(commit=False)

            # Assign the selected product to the inventory item
            inventory.product = product
            try:
                inventory.save()
                messages.success(
                    request, "Inventory added successfully!", extra_tags="bg-success"
                )
                return redirect("inventory:inventory_list")  # Adjust redirect as needed
            except IntegrityError as e:
                messages.error(
                    request, f"Error saving inventory: {str(e)}", extra_tags="bg-danger"
                )
                return redirect("inventory:inventory_add")

    else:
        form = InventoryForm()

    context["form"] = form
    return render(request, "inventory/inventory_add.html", context)


# =================================== Inventory Update view ===================================
@login_required
@admin_or_manager_or_staff_required
def inventory_update_view(request, pk):
    context = {
        "table_title": "Update Inventory",
    }
    inventory = get_object_or_404(Inventory, pk=pk)
    if request.method == "POST":
        form = InventoryForm(request.POST, instance=inventory)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Inventory updated successfully!", extra_tags="bg-success"
            )
            return redirect("inventory:inventory_list")
    else:
        form = InventoryForm(instance=inventory)
        context["form"] = form
    return render(request, "inventory/inventory_update.html", context=context)


# =================================== Inventory Delete view ===================================
@login_required
@admin_required
def inventory_delete_view(request, pk):
    inventory = get_object_or_404(Inventory, pk=pk)
    if request.method == "POST":
        inventory.delete()
        messages.success(
            request, "Inventory deleted successfully!", extra_tags="bg-warning"
        )
        return redirect("inventory:inventory_list")
    return render(
        request, "inventory/inventory_confirm_delete.html", {"inventory": inventory}
    )
