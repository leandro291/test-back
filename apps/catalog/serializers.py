from urllib.parse import urlparse

from django.utils.text import slugify
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    """Read and write representation of a flat catalog category."""

    name = serializers.CharField(
        max_length=100,
        validators=[UniqueValidator(queryset=Category.objects.all())],
    )
    slug = serializers.SlugField(
        max_length=120,
        required=False,
        validators=[UniqueValidator(queryset=Category.objects.all())],
    )

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

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


class CategorySlimSerializer(serializers.ModelSerializer):
    """Minimal nested representation of a category."""

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class ProductReadSerializer(serializers.ModelSerializer):
    """Read representation of a product with its nested category."""

    category = CategorySlimSerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock', 'is_active',
            'image_url', 'category', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductWriteSerializer(serializers.ModelSerializer):
    """Write representation of a product; the category must be a live one."""

    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock', 'is_active',
            'image_url', 'category',
        ]
        read_only_fields = ['id']

    def validate_price(self, value):
        """Reject negative prices with a clean field error."""
        if value < 0:
            raise serializers.ValidationError('Price cannot be negative.')
        return value

    def validate_image_url(self, value):
        """When provided, the URL host must belong to Cloudinary."""
        if value and 'cloudinary.com' not in (urlparse(value).hostname or ''):
            raise serializers.ValidationError(
                'The image URL must be hosted on cloudinary.com.'
            )
        return value
