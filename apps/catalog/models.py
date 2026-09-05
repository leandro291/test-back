from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint
from django.utils.text import slugify

from apps.core.models import BaseModel, SoftDeleteManager, SoftDeleteQuerySet


class CategoryQuerySet(SoftDeleteQuerySet):
    """Reusable queries for Category."""

    def active(self):
        """Return only publicly visible categories."""
        return self.filter(is_active=True)


class Category(BaseModel):
    """Flat category used to classify catalog products."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    objects = SoftDeleteManager.from_queryset(CategoryQuerySet)()
    all_objects = CategoryQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        db_table = 'categories'
        ordering = ['name']
        verbose_name_plural = 'categories'
        constraints = [
            UniqueConstraint(
                fields=['name'],
                condition=Q(deleted_at__isnull=True),
                name='uniq_category_name_alive',
            ),
            UniqueConstraint(
                fields=['slug'],
                condition=Q(deleted_at__isnull=True),
                name='uniq_category_slug_alive',
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Autogenerate the slug from the name when it is not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductQuerySet(SoftDeleteQuerySet):
    """Reusable queries for Product; compose on top of the manager's alive() scope."""

    def active(self):
        """Return only products flagged as publicly visible."""
        return self.filter(is_active=True)

    def in_stock(self):
        """Return only products with available stock."""
        return self.filter(stock__gt=0)

    def with_category(self):
        """Select the related category to avoid N+1 queries."""
        return self.select_related('category')

    def visible(self):
        """Return products publicly visible: active, with a live and active category."""
        return self.active().filter(
            category__is_active=True, category__deleted_at__isnull=True
        )


class Product(BaseModel):
    """A product the store sells, classified by a single category."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    image_url = models.URLField(max_length=500, blank=True)
    category = models.ForeignKey(
        'catalog.Category',
        on_delete=models.PROTECT,
        related_name='products',
    )

    objects = SoftDeleteManager.from_queryset(ProductQuerySet)()
    all_objects = ProductQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        db_table = 'products'
        ordering = ['name']
        constraints = [
            CheckConstraint(
                condition=Q(price__gte=0),
                name='product_price_non_negative',
            ),
        ]

    def __str__(self):
        return self.name
