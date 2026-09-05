from django.db import models
from django.db.utils import OperationalError, ProgrammingError

from apps.core.models import BaseModel


class RoleQuerySet(models.QuerySet):
    """Reusable queries for Role."""

    def with_user_count(self):
        """Annotate each role with the number of users assigned to it."""
        return self.annotate(user_count=models.Count('users'))


class Role(BaseModel):
    """Business role a user can hold in the ecommerce (customer, seller, admin)."""

    code = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)

    objects = RoleQuerySet.as_manager()

    class Meta:
        db_table = 'roles'
        ordering = ['name']

    def __str__(self):
        return self.name


def get_default_role():
    """Return the pk of the default 'customer' role, creating it if missing. User.role default."""
    try:
        return Role.objects.get_or_create(
            code='customer',
            defaults={'name': 'Customer'},
        )[0].pk
    except (OperationalError, ProgrammingError):
        # The roles table does not exist yet (e.g. system checks run before migrate
        # on a fresh database). The field is nullable until 0004; data migrations backfill it.
        return None
