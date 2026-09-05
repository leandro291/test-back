from django_filters import rest_framework as filters

from .models import Role


class RoleFilter(filters.FilterSet):
    """Filter roles by exact code and partial name."""

    name = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Role
        fields = ['code', 'name']
