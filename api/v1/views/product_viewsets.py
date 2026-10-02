from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny

from api.v1.serializers.product_serializers import CategorySerializer, ProductSerializer
from services.product_service import product_service


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "id"]

    def get_queryset(self):
        return product_service.get_categories()


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "category__name", "productvolume__sku"]
    ordering_fields = ["name", "created_at", "is_featured"]

    def get_queryset(self):
        featured = self.request.query_params.get("is_featured")
        if featured is not None:
            featured = featured.lower() in {"1", "true", "yes"}
        return product_service.get_products(
            search=self.request.query_params.get("search", ""),
            category=self.request.query_params.get("category"),
            featured=featured,
        )
