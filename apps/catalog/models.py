from django.db import models
from django.utils.text import slugify

from apps.core.models import BaseModel


class CategoryQuerySet(models.QuerySet):
    """Reusable queries for Category."""

    def active(self):
        """Return only publicly visible categories."""
        return self.filter(is_active=True)


class Category(BaseModel):
    """Flat category used to classify catalog products."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    objects = CategoryQuerySet.as_manager()

    class Meta:
        db_table = 'categories'
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Autogenerate the slug from the name when it is not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
