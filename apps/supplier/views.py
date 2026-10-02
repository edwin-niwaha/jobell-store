import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import Supplier
from .forms import SupplierForm
from apps.authentication.decorators import (
    admin_or_manager_or_staff_required,
    admin_required,
)

logger = logging.getLogger(__name__)


# =================================== supplier list view ===================================
@login_required
@admin_or_manager_or_staff_required
def supplier_list(request):
    search_query = request.GET.get("search", "")  # Get search query from GET parameters

    # If a search query exists, filter the suppliers by name or contact_name
    if search_query:
        suppliers = Supplier.objects.filter(
            name__icontains=search_query
        ) | Supplier.objects.filter(contact_name__icontains=search_query)
    else:
        suppliers = Supplier.objects.all()  # No search query, return all suppliers

    # Paginate the filtered list of suppliers
    paginator = Paginator(suppliers, 25)
    page_number = request.GET.get(
        "page"
    )  # Get the page number from the URL query parameter
    page_obj = paginator.get_page(
        page_number
    )  # Get the page object for the current page

    # Set a table title for the template context
    table_title = "Suppliers List"

    return render(
        request,
        "supplier/suppliers.html",
        {
            "page_obj": page_obj,
            "search_query": search_query,
            "table_title": table_title,  # Add table title to context
        },
    )


# =================================== supplier add view ===================================
@login_required
@admin_or_manager_or_staff_required
def supplier_add(request):
    form_title = "Add New Supplier"
    form = SupplierForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            supplier = form.save()
            messages.success(
                request,
                f'Supplier "{supplier.name}" added successfully.',
                extra_tags="bg-success",
            )
            return redirect("supplier:supplier_list")

    return render(
        request, "supplier/supplier_add.html", {"form": form, "form_title": form_title}
    )


# =================================== supplier update view ===================================
@login_required
@admin_or_manager_or_staff_required
def supplier_update(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    form_title = "Update Supplier"
    form = SupplierForm(request.POST or None, instance=supplier)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.save()
            messages.success(
                request, "Supplier updated successfully!", extra_tags="bg-success"
            )
            return redirect("supplier:supplier_list")

    return render(
        request,
        "supplier/supplier_update.html",
        {"form": form, "form_title": form_title},
    )


# =================================== supplier delete view ===================================
@login_required
@admin_required
def supplier_delete(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)

    try:
        supplier.delete()
        messages.success(
            request, f"Supplier: {supplier.name} deleted!", extra_tags="bg-danger"
        )
    except Exception:
        logger.exception("Error deleting supplier %s", supplier_id)
        messages.error(
            request, "There was an error during the deletion!", extra_tags="bg-danger"
        )

    return redirect("supplier:supplier_list")
