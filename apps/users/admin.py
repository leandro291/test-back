from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """User admin exposing the business role."""

    list_display = BaseUserAdmin.list_display + ('role',)
    list_filter = BaseUserAdmin.list_filter + ('role',)
    list_select_related = ('role',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Business role', {'fields': ('role',)}),
    )
