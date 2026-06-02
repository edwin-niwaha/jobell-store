from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DeliveryRateForm, PickupStationForm
from .models import DeliveryRate, PickupStation


def permission_required_any(*permissions):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or any(user.has_perm(perm) for perm in permissions):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return wrapper

    return decorator


@login_required
@permission_required_any(
    "shipping.view_deliveryrate",
    "shipping.add_deliveryrate",
    "shipping.change_deliveryrate",
)
def delivery_rate_list(request):
    search_query = request.GET.get("search", "").strip()
    rates = DeliveryRate.objects.all()
    if search_query:
        rates = rates.filter(
            Q(city__icontains=search_query)
            | Q(area__icontains=search_query)
            | Q(region__icontains=search_query)
        )

    paginator = Paginator(rates, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "shipping/delivery_rate_list.html",
        {"page_obj": page_obj, "search_query": search_query},
    )


@login_required
@permission_required_any("shipping.add_deliveryrate")
def delivery_rate_add(request):
    form = DeliveryRateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Shipping fee added successfully.", extra_tags="bg-success")
        return redirect("shipping:delivery_rate_list")

    return render(
        request,
        "shipping/shipping_form.html",
        {
            "form": form,
            "form_title": "Add Shipping Fee",
            "back_url": "shipping:delivery_rate_list",
            "submit_label": "Add Shipping Fee",
        },
    )


@login_required
@permission_required_any("shipping.change_deliveryrate")
def delivery_rate_update(request, pk):
    rate = get_object_or_404(DeliveryRate, pk=pk)
    form = DeliveryRateForm(request.POST or None, instance=rate)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Shipping fee updated successfully.", extra_tags="bg-success")
        return redirect("shipping:delivery_rate_list")

    return render(
        request,
        "shipping/shipping_form.html",
        {
            "form": form,
            "form_title": "Update Shipping Fee",
            "back_url": "shipping:delivery_rate_list",
            "submit_label": "Update Shipping Fee",
        },
    )


@login_required
@permission_required_any(
    "shipping.view_pickupstation",
    "shipping.add_pickupstation",
    "shipping.change_pickupstation",
)
def pickup_station_list(request):
    search_query = request.GET.get("search", "").strip()
    stations = PickupStation.objects.all()
    if search_query:
        stations = stations.filter(
            Q(name__icontains=search_query)
            | Q(city__icontains=search_query)
            | Q(area__icontains=search_query)
            | Q(address__icontains=search_query)
        )

    paginator = Paginator(stations, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "shipping/pickup_station_list.html",
        {"page_obj": page_obj, "search_query": search_query},
    )


@login_required
@permission_required_any("shipping.add_pickupstation")
def pickup_station_add(request):
    form = PickupStationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pickup station added successfully.", extra_tags="bg-success")
        return redirect("shipping:pickup_station_list")

    return render(
        request,
        "shipping/shipping_form.html",
        {
            "form": form,
            "form_title": "Add Pickup Station",
            "back_url": "shipping:pickup_station_list",
            "submit_label": "Add Pickup Station",
        },
    )


@login_required
@permission_required_any("shipping.change_pickupstation")
def pickup_station_update(request, pk):
    station = get_object_or_404(PickupStation, pk=pk)
    form = PickupStationForm(request.POST or None, instance=station)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Pickup station updated successfully.", extra_tags="bg-success")
        return redirect("shipping:pickup_station_list")

    return render(
        request,
        "shipping/shipping_form.html",
        {
            "form": form,
            "form_title": "Update Pickup Station",
            "back_url": "shipping:pickup_station_list",
            "submit_label": "Update Pickup Station",
        },
    )
