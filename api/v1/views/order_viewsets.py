from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action

from api.v1.responses import api_response
from api.v1.serializers.order_serializers import (
    CartItemSerializer,
    CartSerializer,
    CheckoutSerializer,
    CustomerAddressSerializer,
    OrderSerializer,
    WishlistItemSerializer,
)
from apps.addresses.models import CustomerAddress
from services.order_service import (
    cart_service,
    checkout_service,
    order_service,
    wishlist_service,
)


class CartViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return api_response(CartSerializer(cart_service.get_cart(request.user)).data)

    def create(self, request):
        return api_response(CartSerializer(cart_service.get_cart(request.user)).data)


class CartItemViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        return api_response(CartItemSerializer(cart_service.get_cart_items(request.user), many=True).data)

    def create(self, request):
        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = cart_service.add_item(
                user=request.user,
                variant_id=serializer.validated_data["variant_id"],
                quantity=serializer.validated_data.get("quantity", 1),
            )
        except DjangoValidationError as exc:
            return api_response({}, str(exc), False, status.HTTP_400_BAD_REQUEST)
        return api_response(CartItemSerializer(item).data, "Item added to cart", status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        try:
            item = cart_service.update_item(
                user=request.user,
                item_id=pk,
                quantity=request.data.get("quantity", 1),
            )
        except DjangoValidationError as exc:
            return api_response({}, str(exc), False, status.HTTP_400_BAD_REQUEST)
        if item is None:
            return api_response({}, "Item removed")
        return api_response(CartItemSerializer(item).data, "Cart item updated")

    def destroy(self, request, pk=None):
        cart_service.remove_item(user=request.user, item_id=pk)
        return api_response({}, "Item removed", status=status.HTTP_204_NO_CONTENT)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return order_service.get_orders(self.request.user)

    @action(detail=False, methods=["post"], url_path="checkout")
    def checkout(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order = checkout_service.checkout(user=request.user, **serializer.validated_data)
        except (DjangoValidationError, ValueError) as exc:
            return api_response({}, str(exc), False, status.HTTP_400_BAD_REQUEST)
        return api_response(OrderSerializer(order).data, "Order created", status=status.HTTP_201_CREATED)


class CheckoutViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        data = checkout_service.get_summary(
            user=request.user,
            address_id=request.query_params.get("address_id"),
            delivery_option=request.query_params.get("delivery_option", "HOME_DELIVERY"),
            pickup_station_id=request.query_params.get("pickup_station_id"),
        )
        return api_response(data)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CustomerAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WishlistItemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WishlistItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return wishlist_service.list_items(self.request.user)
