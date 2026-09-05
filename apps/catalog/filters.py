from django_filters import rest_framework as filters

from .models import Category, Product


class CategoryFilter(filters.FilterSet):
    """Filter categories by partial name and exact active flag."""

    name = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Category
        fields = ['name', 'is_active']


class ProductFilter(filters.FilterSet):
    """Filter products by category, price range, active flag and stock availability."""

    category = filters.NumberFilter(field_name='category_id')
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte')
    in_stock = filters.BooleanFilter(method='filter_in_stock')

    class Meta:
        model = Product
        fields = ['category', 'is_active']

    def filter_in_stock(self, queryset, name, value):
        """When true, keep only products with stock greater than zero."""
        if value:
            return queryset.in_stock()
        return queryset
