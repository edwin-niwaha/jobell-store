from django.urls import path

from . import views

app_name = "addresses"

urlpatterns = [
    path("", views.address_list, name="list"),
    path("add/", views.address_create, name="create"),
    path("<int:pk>/edit/", views.address_update, name="update"),
    path("<int:pk>/delete/", views.address_delete, name="delete"),
    path("<int:pk>/default/", views.address_make_default, name="make_default"),
]

