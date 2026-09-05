from django.db import models


class BaseModel(models.Model):
    """Abstract base with created/updated timestamps. Inherit everywhere."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']
