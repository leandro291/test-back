from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for flat catalog categories."""

    list_display = ('name', 'slug', 'is_active', 'deleted_at')
    list_filter = ('is_active', 'deleted_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    actions = ('restore',)

    def get_queryset(self, request):
        return Category.all_objects.all()

    @admin.action(description='Restore selected categories')
    def restore(self, request, queryset):
        """Revive the selected soft-deleted categories."""
        queryset.update(deleted_at=None)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin for catalog products; shows soft-deleted rows too."""

    list_display = ('name', 'category', 'price', 'stock', 'is_active', 'deleted_at')
    list_filter = ('is_active', 'category', 'deleted_at')
    search_fields = ('name',)
    list_select_related = ('category',)
    autocomplete_fields = ('category',)
    actions = ('restore',)

    def get_queryset(self, request):
        return Product.all_objects.select_related('category')

    @admin.action(description='Restore selected products')
    def restore(self, request, queryset):
        """Revive the selected soft-deleted products."""
        queryset.update(deleted_at=None)
