from django.db import models
from django.db.models import Q, UniqueConstraint
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
