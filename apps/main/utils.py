from django.db.models import Sum, F
from apps.products.models import Product


def get_top_selling_products():
    return (
        Product.objects.annotate(
            total_quantity_sold=Sum("saledetail__quantity"),
            total_sales_value=Sum(F("saledetail__total_detail")),
        )
        .filter(total_quantity_sold__gt=0)  # Only include products that have been sold
        .order_by("-total_quantity_sold")[:9]
    )
