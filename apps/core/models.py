from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet whose delete() is a soft delete, plus alive/dead filters and hard_delete()."""

    def alive(self):
        """Rows that have not been soft-deleted."""
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        """Rows that have been soft-deleted."""
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        """Soft delete every row in the queryset; keeps the DELETE return shape (n, {})."""
        return self.update(deleted_at=timezone.now()), {}

    def hard_delete(self):
        """Physically delete the rows with Django's normal cascade."""
        return super().delete()


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Default manager: hides soft-deleted rows."""

    def get_queryset(self):
        return super().get_queryset().alive()


class BaseModel(models.Model):
    """Abstract base with created/updated timestamps and soft delete. Inherit everywhere."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ['-created_at']
        base_manager_name = 'all_objects'

    def delete(self, using=None, keep_parents=False):
        """Soft delete: stamp deleted_at, keep the row. Does not call super()."""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        """Physically delete the row from the database."""
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Undo a soft delete."""
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])
