from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.roles.models import get_default_role


class User(AbstractUser):
    """Custom user: email is the login field."""

    email = models.EmailField(unique=True)
    role = models.ForeignKey(
        'roles.Role',
        on_delete=models.PROTECT,
        related_name='users',
        default=get_default_role,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.email
