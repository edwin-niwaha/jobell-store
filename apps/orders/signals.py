from django.contrib.auth import user_logged_in
from django.dispatch import receiver
from .models import Cart, CartItem


@receiver(user_logged_in)
def merge_carts(sender, user, request, **kwargs):
    session_key = request.session.get("session_key")
    if session_key:
        anonymous_cart = Cart.objects.filter(session_key=session_key, user=None).first()
        if anonymous_cart:
            user_cart, _ = Cart.objects.get_or_create(user=user, session_key=None)
            for item in anonymous_cart.items.all():
                user_item, created = CartItem.objects.get_or_create(
                    cart=user_cart, product=item.product, volume=item.volume
                )
                if not created:
                    user_item.quantity += item.quantity
                    user_item.save()
                else:
                    user_item.quantity = item.quantity
                    user_item.save()
            anonymous_cart.delete()
            request.session.pop("session_key", None)
            request.session.modified = True
