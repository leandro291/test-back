from django.contrib import admin

from .models import Category


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
