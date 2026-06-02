from django.urls import path

from . import views

app_name = "shipping"

urlpatterns = [
    path("delivery-rates/", views.delivery_rate_list, name="delivery_rate_list"),
    path("delivery-rates/add/", views.delivery_rate_add, name="delivery_rate_add"),
    path(
        "delivery-rates/<int:pk>/update/",
        views.delivery_rate_update,
        name="delivery_rate_update",
    ),
    path("pickup-stations/", views.pickup_station_list, name="pickup_station_list"),
    path("pickup-stations/add/", views.pickup_station_add, name="pickup_station_add"),
    path(
        "pickup-stations/<int:pk>/update/",
        views.pickup_station_update,
        name="pickup_station_update",
    ),
]
