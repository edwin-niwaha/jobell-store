# urls.py
from django.urls import path
from .views import (
    inventory_list_view,
    inventory_add_view,
    inventory_update_view,
    inventory_delete_view,
    inventory_report_view,
)

app_name = "inventory"

urlpatterns = [
    path("", inventory_list_view, name="inventory_list"),
    path("inventory-report/", inventory_report_view, name="inventory-report"),
    path("add/", inventory_add_view, name="inventory_add"),
    path("update/<int:pk>/", inventory_update_view, name="inventory_update"),
    path("delete/<int:pk>/", inventory_delete_view, name="inventory_delete"),
]
