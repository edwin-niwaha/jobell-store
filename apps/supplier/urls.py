# urls.py
from django.urls import path

from . import views

app_name = "supplier"
urlpatterns = [
    path("", views.supplier_list, name="supplier_list"),
    path("add/", views.supplier_add, name="supplier_add"),
    path("update/<int:supplier_id>/", views.supplier_update, name="supplier_update"),
    path("delete/<int:supplier_id>/", views.supplier_delete, name="supplier_delete"),
]
