from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.core.permissions import IsAdminOrReadOnly

from .filters import CategoryFilter, ProductFilter
from .models import Category, Product
from .serializers import (
    CategorySerializer,
    ProductReadSerializer,
    ProductWriteSerializer,
)


class CategoryViewSet(viewsets.ModelViewSet):
    """CRUD for flat catalog categories: public read, staff write."""

    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = CategoryFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """Staff sees every category; everyone else only the active ones."""
        queryset = Category.objects.all()
        user = self.request.user
        if not (user and user.is_staff):
            queryset = queryset.active()
        return queryset

    def destroy(self, request, *args, **kwargs):
        """Soft delete unless the category still has live products (then 409)."""
        instance = self.get_object()
        if instance.products.exists():
            return Response(
                {'detail': 'No se puede eliminar una categoría con productos asociados.'},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)


class ProductViewSet(viewsets.ModelViewSet):
    """CRUD for catalog products: public read, staff write."""

    permission_classes = [IsAdminOrReadOnly]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ProductWriteSerializer
        return ProductReadSerializer

    def get_queryset(self):
        """Staff sees every live product; everyone else only the visible ones."""
        queryset = Product.objects.with_category()
        user = self.request.user
        if not (user and user.is_staff):
            queryset = queryset.visible()
        return queryset
