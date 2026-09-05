from django.contrib import admin

from .models import Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin for business roles. code is immutable once the role exists."""

    list_display = ('code', 'name', 'user_count')
    search_fields = ('code', 'name')

    def get_queryset(self, request):
        return super().get_queryset(request).with_user_count()

    @admin.display(ordering='user_count', description='users')
    def user_count(self, obj):
        return obj.user_count

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return ('code',)
        return ()
