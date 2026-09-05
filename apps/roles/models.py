from django.db import models
from django.db.models import Q, UniqueConstraint
from django.db.utils import OperationalError, ProgrammingError

from apps.core.models import BaseModel, SoftDeleteManager, SoftDeleteQuerySet


class RoleQuerySet(SoftDeleteQuerySet):
    """Reusable queries for Role."""

    def with_user_count(self):
        """Annotate each role with the number of users assigned to it."""
        return self.annotate(user_count=models.Count('users'))


class Role(BaseModel):
    """Business role a user can hold in the ecommerce (customer, seller, admin)."""

    code = models.SlugField(max_length=32)
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)

    objects = SoftDeleteManager.from_queryset(RoleQuerySet)()
    all_objects = RoleQuerySet.as_manager()

    class Meta(BaseModel.Meta):
        db_table = 'roles'
        ordering = ['name']
        constraints = [
            UniqueConstraint(
                fields=['code'],
                condition=Q(deleted_at__isnull=True),
                name='uniq_role_code_alive',
            ),
        ]

    def __str__(self):
        return self.name


def get_default_role():
    """Return the pk of the default 'customer' role, creating or restoring it if needed."""
    try:
        role, _ = Role.all_objects.get_or_create(
            code='customer',
            defaults={'name': 'Customer'},
        )
    except (OperationalError, ProgrammingError):
        # The roles table does not exist yet (e.g. system checks run before migrate
        # on a fresh database). The field is nullable until 0004; data migrations backfill it.
        return None
    if role.deleted_at is not None:
        role.restore()
    return role.pk
