from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CustomerAddressForm
from .models import CustomerAddress


@login_required
def address_list(request):
    addresses = CustomerAddress.objects.filter(user=request.user)
    return render(
        request,
        "addresses/address_list.html",
        {"addresses": addresses},
    )


@login_required
def address_create(request):
    form = CustomerAddressForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        if not CustomerAddress.objects.filter(user=request.user).exists():
            address.is_default = True
        address.save()
        messages.success(request, "Address saved successfully.", extra_tags="bg-success")
        return redirect("addresses:list")
    return render(request, "addresses/address_form.html", {"form": form})


@login_required
def address_update(request, pk):
    address = get_object_or_404(CustomerAddress, pk=pk, user=request.user)
    form = CustomerAddressForm(request.POST or None, instance=address)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Address updated successfully.", extra_tags="bg-success")
        return redirect("addresses:list")
    return render(request, "addresses/address_form.html", {"form": form, "address": address})


@login_required
def address_delete(request, pk):
    address = get_object_or_404(CustomerAddress, pk=pk, user=request.user)
    if request.method == "POST":
        address.delete()
        messages.success(request, "Address deleted successfully.", extra_tags="bg-success")
        return redirect("addresses:list")
    return render(request, "addresses/address_confirm_delete.html", {"address": address})


@login_required
def address_make_default(request, pk):
    address = get_object_or_404(CustomerAddress, pk=pk, user=request.user)
    address.is_default = True
    address.save(update_fields=["is_default", "updated_at"])
    messages.success(request, "Default address updated.", extra_tags="bg-success")
    return redirect("addresses:list")

