from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Role


class RoleSerializer(serializers.ModelSerializer):
    """Read and create representation of a role, including its user count."""

    code = serializers.SlugField(
        max_length=32,
        validators=[UniqueValidator(queryset=Role.objects.all())],
    )
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id', 'code', 'name', 'description', 'user_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_user_count(self, obj) -> int:
        """Use the annotated value from the list queryset; fall back to a count."""
        count = getattr(obj, 'user_count', None)
        return count if count is not None else obj.users.count()


class RoleUpdateSerializer(RoleSerializer):
    """Update representation: code is immutable after creation."""

    code = serializers.SlugField(read_only=True)
