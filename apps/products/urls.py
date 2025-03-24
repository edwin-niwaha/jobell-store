# urls.py
from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    # ** Category URLs **
    path("categories/", views.categories_list_view, name="categories_list"),
    path("categories/add/", views.categories_add_view, name="categories_add"),
    path(
        "categories/update/<str:category_id>/",
        views.categories_update_view,
        name="categories_update",
    ),
    path(
        "categories/delete/<str:category_id>/",
        views.categories_delete_view,
        name="categories_delete",
    ),
    # ** Volume URLs **
    path("volume/list", views.volume_list, name="volume_list"),
    path("volume/add/", views.volume_add_view, name="volume_add"),
    path(
        "delete_volume/<int:volume_id>/", views.delete_volume_view, name="delete_volume"
    ),
    path(
        "volume/update/<int:volume_id>/", views.volume_update_view, name="volume_update"
    ),
    path(
        "filtered-volumes/",
        views.product_volumes_list_view,
        name="product-volumes-list",
    ),
    # ** Product Volume URLs **
    path(
        "volume/add/<int:product_id>/",
        views.add_product_volume_view,
        name="add_product_volume",
    ),
    path(
        "product_volume/update/<int:product_id>/<int:volume_id>/",
        views.update_product_volume_view,
        name="update_product_volume",
    ),
    path(
        "products/<int:product_id>/volumes/",
        views.product_volume_list_view,
        name="product_volume_list",
    ),
    path(
        "volumes/<int:volume_id>/delete/",
        views.delete_product_volume_view,
        name="delete_product_volume",
    ),
    path(
        "add-volume-to-all-products/",
        views.add_volume_to_all_products_view,
        name="add-volume-to-all-products",
    ),
    path(
        "delete-volumes/",
        views.delete_selected_volumes_view,
        name="delete-selected-volumes",
    ),
    # ** Product URLs **
    path("all", views.products_list_all, name="products_list_all"),
    path("", views.products_list_view, name="products_list"),
    path("add/", views.products_add_view, name="products_add"),
    path(
        "update/<str:product_id>/", views.products_update_view, name="products_update"
    ),
    path(
        "delete/<str:product_id>/", views.products_delete_view, name="products_delete"
    ),
    # ** Product Image URLs **
    path("product-image/", views.update_product_image, name="update_product_image"),
    path("product-image/list/", views.product_images, name="product_images"),
    path(
        "product-image/delete/<int:pk>/",
        views.delete_product_image,
        name="delete_product_image",
    ),
    # ** Stock Alerts **
    path("stock-alerts/", views.stock_alerts_view, name="stock_alerts"),
    path("discounted/", views.discounted_product_list_view, name="discounted_products"),
    path("shop-now", views.shop_homepage_view, name="shop_homepage"),
    # Other URL patterns for product details
]
