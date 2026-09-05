from rest_framework import viewsets

from apps.core.permissions import IsAdminOrReadOnly

from .filters import CategoryFilter
from .models import Category
from .serializers import CategorySerializer


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
