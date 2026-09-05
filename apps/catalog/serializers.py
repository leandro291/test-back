from django.utils.text import slugify
from rest_framework import serializers

from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    """Read and write representation of a flat catalog category."""

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {'slug': {'required': False}}

    def validate(self, attrs):
        """Fill the slug from the name when omitted and reject collisions with 400, not 500."""
        if not attrs.get('slug'):
            name = attrs.get('name') or getattr(self.instance, 'name', '')
            candidate = slugify(name)
            if candidate:
                qs = Category.objects.filter(slug=candidate)
                if self.instance is not None:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise serializers.ValidationError(
                        {'slug': 'category with this slug already exists.'}
                    )
                attrs['slug'] = candidate
        return attrs
