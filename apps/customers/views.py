import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from .models import Customer
from .forms import CustomerForm

# Import custom decorators
from apps.authentication.decorators import (
    admin_or_manager_or_staff_required,
    admin_required,
)

logger = logging.getLogger(__name__)


# =================================== customers list view ===================================
@login_required
@admin_or_manager_or_staff_required
def customers_list_view(request):
    search_query = request.GET.get("search", "").strip()
    customers = Customer.objects.select_related("user").all()
    if search_query:
        customers = customers.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(mobile__icontains=search_query)
            | Q(tel__icontains=search_query)
        )
    paginator = Paginator(customers, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "active_icon": "customers",
        "customers": page_obj,
        "page_obj": page_obj,
        "search_query": search_query,
        "table_title": "Customers",
    }
    return render(request, "customers/customers.html", context)


# =================================== customers add view ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def customers_add_view(request):
    context = {
        "table_title": "Add Customer",
    }

    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            # Check for existing customer with the same attributes
            attributes = form.cleaned_data
            if Customer.objects.filter(**attributes).exists():
                messages.error(
                    request, "Customer already exists!", extra_tags="bg-warning"
                )
                return redirect("customers:customers_add")

            try:
                # Save the new customer
                new_customer = form.save()
                messages.success(
                    request,
                    f"Customer: {new_customer.first_name} {new_customer.last_name} created successfully!",
                    extra_tags="bg-success",
                )
                return redirect("customers:customers_list")
            except Exception:
                logger.exception("Error creating customer")
                messages.error(
                    request,
                    "There was an error during the creation!",
                    extra_tags="bg-danger",
                )
                return redirect("customers:customers_add")
        else:
            messages.error(
                request, "Please correct the errors below.", extra_tags="bg-danger"
            )
    else:
        form = CustomerForm()

    context["form"] = form
    return render(request, "customers/customers_add.html", context=context)


# =================================== customers update view ===================================
@login_required
@admin_or_manager_or_staff_required
@transaction.atomic
def customers_update_view(request, customer_id):
    # Retrieve the customer by ID
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            # Check if a customer with the same email exists, excluding the current customer
            if (
                Customer.objects.exclude(id=customer_id)
                .filter(email=form.cleaned_data["email"])
                .exists()
            ):
                messages.error(
                    request,
                    "A customer with this email already exists!",
                    extra_tags="bg-warning",
                )
                return redirect("customers:customers_update", customer_id=customer_id)

            try:
                # Save the updated customer
                form.save()
                messages.success(
                    request,
                    f"Customer: {customer.get_full_name()} updated successfully!",
                    extra_tags="bg-success",
                )
                return redirect("customers:customers_list")
            except Exception:
                logger.exception("Error updating customer %s", customer_id)
                messages.error(
                    request,
                    "There was an error during the update!",
                    extra_tags="bg-danger",
                )
                return redirect("customers:customers_update", customer_id=customer_id)
        else:
            messages.error(
                request, "Please correct the errors below.", extra_tags="bg-danger"
            )
    else:
        form = CustomerForm(instance=customer)

    context = {
        "active_icon": "customers",
        "form": form,
        "customer": customer,
    }

    return render(request, "customers/customers_update.html", context=context)


# =================================== customers delete view ===================================
@login_required
@admin_required
@transaction.atomic
def customers_delete_view(request, customer_id):
    try:
        # Retrieve and delete the customer
        customer = Customer.objects.get(id=customer_id)
        customer.delete()
        messages.success(
            request,
            f"Customer: {customer.get_full_name()} deleted!",
            extra_tags="bg-success",
        )
        return redirect("customers:customers_list")
    except Exception:
        logger.exception("Error deleting customer %s", customer_id)
        messages.error(
            request,
            "There was an error during the elimination!",
            extra_tags="bg-danger",
        )
        return redirect("customers:customers_list")
