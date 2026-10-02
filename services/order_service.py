from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.addresses.models import CustomerAddress
from apps.orders.models import CartItem
from apps.orders.services import cart_total, create_order_from_cart
from apps.shipping.services import delivery_quote_for
from repositories.order_repository import (
    CartRepository,
    OrderRepository,
    WishlistRepository,
)
from repositories.product_repository import ProductVariantRepository


class CartService:
    def __init__(self, cart_repository=None, variant_repository=None):
        self.cart_repository = cart_repository or CartRepository()
        self.variant_repository = variant_repository or ProductVariantRepository()

    def get_cart(self, user):
        return self.cart_repository.get_or_create_for_user(user)

    def get_cart_items(self, user):
        return self.cart_repository.list_items(self.get_cart(user))

    @transaction.atomic
    def add_item(self, *, user, variant_id, quantity=1):
        quantity = int(quantity or 1)
        if quantity < 1:
            raise ValidationError("Quantity must be at least 1.")

        variant = self.variant_repository.get_active_variant(variant_id)
        if not variant:
            raise ValidationError("Selected product variant is not available.")
        if not variant.is_in_stock:
            raise ValidationError("Selected product variant is out of stock.")
        if variant.max_quantity_per_order and quantity > variant.max_quantity_per_order:
            raise ValidationError(f"You can order up to {variant.max_quantity_per_order} units.")

        cart = self.get_cart(user)
        item, _ = CartItem.objects.select_for_update().get_or_create(
            cart=cart,
            volume=variant,
            defaults={"product": variant.product, "quantity": 0},
        )
        item.product = variant.product
        item.quantity = min(item.quantity + quantity, variant.available_quantity)
        item.save()
        return item

    @transaction.atomic
    def update_item(self, *, user, item_id, quantity):
        item = self.cart_repository.get_item_for_user(user=user, item_id=item_id)
        quantity = int(quantity)
        if quantity < 1:
            item.delete()
            return None
        if item.volume.max_quantity_per_order and quantity > item.volume.max_quantity_per_order:
            raise ValidationError(f"You can order up to {item.volume.max_quantity_per_order} units.")
        if quantity > item.volume.available_quantity:
            raise ValidationError(f"Only {item.volume.available_quantity} units are available.")
        item.quantity = quantity
        item.save(update_fields=["quantity", "updated_at"])
        return item

    def remove_item(self, *, user, item_id):
        item = self.cart_repository.get_item_for_user(user=user, item_id=item_id)
        item.delete()

    def total(self, user):
        return cart_total(self.get_cart(user))


class CheckoutService:
    def __init__(self, cart_service=None):
        self.cart_service = cart_service or CartService()

    def get_summary(self, *, user, address_id=None, delivery_option="HOME_DELIVERY", pickup_station_id=None):
        cart = self.cart_service.get_cart(user)
        subtotal = cart_total(cart)
        shipping_fee = Decimal("0.00")
        address_text = ""
        region = ""

        if address_id:
            address = CustomerAddress.objects.get(id=address_id, user=user)
            address_text = address.single_line
            region = address.region
            if delivery_option == "HOME_DELIVERY":
                quote = delivery_quote_for(
                    region=address.region,
                    city=address.city,
                    area=address.area,
                )
                shipping_fee = quote.fee

        return {
            "items_subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "tax_amount": Decimal("0.00"),
            "total_price": subtotal + shipping_fee,
            "delivery_address_text": address_text,
            "delivery_region": region,
        }

    def checkout(self, *, user, address_id, delivery_option="HOME_DELIVERY", pickup_station_id=None, payment_method="cod", description=""):
        address = CustomerAddress.objects.get(id=address_id, user=user)
        summary = self.get_summary(
            user=user,
            address_id=address.id,
            delivery_option=delivery_option,
            pickup_station_id=pickup_station_id,
        )
        shipping_method = "pickup" if delivery_option == "PICKUP_STATION" else "delivery"
        order = create_order_from_cart(
            self.cart_service.get_cart(user),
            customer_data={
                "first_name": user.first_name or user.username,
                "last_name": user.last_name,
                "email": user.email,
                "mobile": address.phone_number,
                "address": address.single_line,
            },
            payment_method="mobile" if str(payment_method).lower() in {"mobile", "mtn", "card"} else "cod",
            shipping_data={
                "shipping_method": shipping_method,
                "shipping_fee": summary["shipping_fee"],
                "delivery_address_text": summary["delivery_address_text"],
                "delivery_region": summary["delivery_region"],
            },
        )
        if description:
            order.delivery_address_text = f"{order.delivery_address_text}\n{description}".strip()
            order.save(update_fields=["delivery_address_text", "updated_at"])
        return order


class OrderService:
    def __init__(self, repository=None):
        self.repository = repository or OrderRepository()

    def get_orders(self, user):
        return self.repository.list_for_user(user)

    def get_order(self, *, user, order_id):
        return self.repository.get_for_user(user=user, order_id=order_id)


class WishlistService:
    def __init__(self, repository=None):
        self.repository = repository or WishlistRepository()

    def list_items(self, user):
        return self.repository.list_for_user(user)


cart_service = CartService()
checkout_service = CheckoutService(cart_service=cart_service)
order_service = OrderService()
wishlist_service = WishlistService()
