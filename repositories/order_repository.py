from apps.orders.models import Cart, CartItem, Order, Wishlist


class CartRepository:
    def get_or_create_for_user(self, user):
        cart, _ = Cart.objects.get_or_create(user=user, session_key=None)
        return cart

    def list_items(self, cart):
        return cart.items.select_related("product", "volume", "volume__volume").prefetch_related(
            "product__images"
        )

    def get_item_for_user(self, *, user, item_id):
        return CartItem.objects.select_related("cart", "product", "volume").get(
            id=item_id,
            cart__user=user,
        )


class OrderRepository:
    def list_for_user(self, user):
        return (
            Order.objects.select_related("customer", "pickup_station")
            .prefetch_related("details__product", "details__product_volume__volume")
            .filter(customer__user=user)
            .order_by("-created_at")
        )

    def get_for_user(self, *, user, order_id):
        return self.list_for_user(user).get(id=order_id)


class WishlistRepository:
    def list_for_user(self, user):
        return Wishlist.objects.select_related("product", "product__category").filter(user=user)
