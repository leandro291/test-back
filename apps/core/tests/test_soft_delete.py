from django.test import TestCase

from apps.catalog.models import Category


class SoftDeleteTests(TestCase):
    """The BaseModel soft delete behaviour, exercised through Category."""

    def test_instance_delete_sets_deleted_at_and_keeps_row(self):
        category = Category.objects.create(name='Beverages')
        category.delete()

        row = Category.all_objects.get(pk=category.pk)
        self.assertIsNotNone(row.deleted_at)

    def test_default_manager_hides_dead_all_objects_sees_them(self):
        category = Category.objects.create(name='Beverages')
        category.delete()

        self.assertFalse(Category.objects.filter(pk=category.pk).exists())
        self.assertTrue(Category.all_objects.filter(pk=category.pk).exists())

    def test_restore_revives_the_row(self):
        category = Category.objects.create(name='Beverages')
        category.delete()
        category.restore()

        self.assertTrue(Category.objects.filter(pk=category.pk).exists())
        self.assertIsNone(Category.all_objects.get(pk=category.pk).deleted_at)

    def test_queryset_delete_marks_in_bulk_without_removing(self):
        Category.objects.create(name='A')
        Category.objects.create(name='B')

        result = Category.objects.all().delete()

        self.assertEqual(result, (2, {}))
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(Category.all_objects.count(), 2)
        self.assertTrue(all(c.deleted_at for c in Category.all_objects.all()))

    def test_instance_hard_delete_removes_row(self):
        category = Category.objects.create(name='A')
        pk = category.pk
        category.hard_delete()

        self.assertFalse(Category.all_objects.filter(pk=pk).exists())

    def test_queryset_hard_delete_removes_rows(self):
        Category.objects.create(name='A')
        Category.objects.create(name='B')

        Category.all_objects.all().hard_delete()

        self.assertEqual(Category.all_objects.count(), 0)

    def test_alive_and_dead_split_the_set(self):
        alive = Category.objects.create(name='Alive')
        dead = Category.objects.create(name='Dead')
        dead.delete()

        self.assertEqual(list(Category.all_objects.alive()), [alive])
        self.assertEqual(list(Category.all_objects.dead()), [dead])
