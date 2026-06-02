from dataclasses import dataclass
from decimal import Decimal

from .models import DeliveryRate


@dataclass(frozen=True)
class DeliveryQuote:
    fee: Decimal
    rate: DeliveryRate | None
    available: bool
    message: str
    match_level: str = ""


def _normalize_region(region):
    region = (region or "").strip()
    if not region:
        return ""

    field = DeliveryRate._meta.get_field("region")
    valid_values = {value for value, _label in field.choices}
    if region in valid_values:
        return region

    normalized = region.casefold()
    for value, label in field.choices:
        if normalized in {value.casefold(), str(label).casefold()}:
            return value
    return region


def find_delivery_rate(region, city="", area=""):
    region = _normalize_region(region)
    city = (city or "").strip()
    area = (area or "").strip()
    candidates = [
        ("area", {"region": region, "city__iexact": city, "area__iexact": area}),
        ("city", {"region": region, "city__iexact": city, "area": ""}),
        ("region", {"region": region, "city": "", "area": ""}),
    ]

    for _level, filters in candidates:
        if ("city__iexact" in filters and not filters["city__iexact"]) or (
            "area__iexact" in filters and not filters["area__iexact"]
        ):
            continue
        rate = DeliveryRate.objects.filter(is_active=True, **filters).first()
        if rate:
            return rate
    return None


def delivery_quote_for(region, city="", area=""):
    region = _normalize_region(region)
    if not region:
        return DeliveryQuote(
            fee=Decimal("0.00"),
            rate=None,
            available=False,
            message="Choose a delivery region to calculate transport.",
        )

    city = (city or "").strip()
    area = (area or "").strip()
    candidates = [
        ("area", {"region": region, "city__iexact": city, "area__iexact": area}),
        ("city", {"region": region, "city__iexact": city, "area": ""}),
        ("region", {"region": region, "city": "", "area": ""}),
    ]

    for match_level, filters in candidates:
        if ("city__iexact" in filters and not filters["city__iexact"]) or (
            "area__iexact" in filters and not filters["area__iexact"]
        ):
            continue
        rate = DeliveryRate.objects.filter(is_active=True, **filters).first()
        if rate:
            return DeliveryQuote(
                fee=rate.fee,
                rate=rate,
                available=True,
                message=f"Delivery fee matched by {match_level}.",
                match_level=match_level,
            )

    return DeliveryQuote(
        fee=Decimal("0.00"),
        rate=None,
        available=False,
        message=(
            "Door delivery is not configured for this location yet. "
            "Choose pickup or contact support for a delivery quote."
        ),
    )


def delivery_fee_for(region, city="", area=""):
    return delivery_quote_for(region, city=city, area=area).fee
