from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from api.v1.docs import mobile_api_docs

from api.v1.views.auth_views import AuthViewSet
from api.v1.views.order_viewsets import (
    AddressViewSet,
    CartItemViewSet,
    CartViewSet,
    CheckoutViewSet,
    OrderViewSet,
    WishlistItemViewSet,
)
from api.v1.views.product_viewsets import CategoryViewSet, ProductViewSet

router = DefaultRouter()
router.register("auth", AuthViewSet, basename="auth")
router.register("categories", CategoryViewSet, basename="categories")
router.register("products", ProductViewSet, basename="products")
router.register("cart", CartViewSet, basename="cart")
router.register("cart-items", CartItemViewSet, basename="cart-items")
router.register("orders", OrderViewSet, basename="orders")
router.register("checkout", CheckoutViewSet, basename="checkout")
router.register("addresses", AddressViewSet, basename="addresses")
router.register("wishlist-items", WishlistItemViewSet, basename="wishlist-items")

urlpatterns = [
    path("docs/", mobile_api_docs, name="mobile_api_docs"),
    path("", include(router.urls)),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
