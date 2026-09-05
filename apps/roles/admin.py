from django.contrib import admin

from .models import Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin for business roles. code is immutable once the role exists."""

    list_display = ('code', 'name', 'user_count', 'deleted_at')
    list_filter = ('deleted_at',)
    search_fields = ('code', 'name')
    actions = ('restore',)

    def get_queryset(self, request):
        return Role.all_objects.with_user_count()

    @admin.display(ordering='user_count', description='users')
    def user_count(self, obj):
        return obj.user_count

    @admin.action(description='Restore selected roles')
    def restore(self, request, queryset):
        """Revive the selected soft-deleted roles."""
        queryset.update(deleted_at=None)

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return ('code',)
        return ()
