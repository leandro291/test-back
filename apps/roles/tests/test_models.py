from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.roles.models import Role, get_default_role

User = get_user_model()


class RoleModelTests(TestCase):
    def test_seed_migration_created_the_base_roles(self):
        self.assertEqual(
            set(Role.objects.values_list('code', flat=True)),
            {'customer', 'seller', 'admin'},
        )

    def test_code_is_unique(self):
        with self.assertRaises(IntegrityError):
            Role.objects.create(code='customer', name='Duplicate')

    def test_str_returns_name(self):
        role = Role.objects.create(code='manager', name='Manager')
        self.assertEqual(str(role), 'Manager')

    def test_get_default_role_is_idempotent(self):
        first = get_default_role()
        second = get_default_role()
        self.assertEqual(first, second)
        self.assertEqual(Role.objects.filter(code='customer').count(), 1)

    def test_with_user_count_annotates(self):
        customer = Role.objects.get(code='customer')
        seller = Role.objects.get(code='seller')
        User.objects.create_user(username='u1', email='u1@x.com', password='x', role=customer)
        User.objects.create_user(username='u2', email='u2@x.com', password='x', role=customer)

        counts = {r.code: r.user_count for r in Role.objects.with_user_count()}
        self.assertEqual(counts['customer'], 2)
        self.assertEqual(counts[seller.code], 0)
