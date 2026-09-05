from django_filters import rest_framework as filters

from .models import Category


class CategoryFilter(filters.FilterSet):
    """Filter categories by partial name and exact active flag."""

    name = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Category
        fields = ['name', 'is_active']
