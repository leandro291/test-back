from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.roles.models import Role

User = get_user_model()


class RoleAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer_role = Role.objects.get(code='customer')
        cls.seller_role = Role.objects.get(code='seller')
        cls.user = User.objects.create_user(
            username='plain', email='plain@x.com', password='x', role=cls.customer_role,
        )
        cls.staff = User.objects.create_user(
            username='staff', email='staff@x.com', password='x', is_staff=True,
            role=cls.customer_role,
        )
        cls.list_url = '/api/v1/roles/'

    def detail_url(self, pk):
        return f'/api/v1/roles/{pk}/'

    # --- read / auth ---

    def test_list_requires_authentication(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_ok_and_paginated_for_non_staff(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)

    def test_filter_by_code(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.list_url, {'code': 'admin'})
        codes = [r['code'] for r in response.data['results']]
        self.assertEqual(codes, ['admin'])

    def test_filter_by_name_icontains(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.list_url, {'name': 'sell'})
        codes = [r['code'] for r in response.data['results']]
        self.assertEqual(codes, ['seller'])

    def test_search_on_description(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(self.list_url, {'search': 'catalog'})
        codes = [r['code'] for r in response.data['results']]
        self.assertEqual(codes, ['seller'])

    def test_user_count_is_annotated(self):
        self.client.force_authenticate(self.user)
        with self.assertNumQueries(2):  # count + page
            response = self.client.get(self.list_url)
        by_code = {r['code']: r['user_count'] for r in response.data['results']}
        self.assertEqual(by_code['customer'], 2)

    # --- write / staff ---

    def test_create_requires_token(self):
        response = self.client.post(self.list_url, {'code': 'x', 'name': 'X'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_forbidden_for_non_staff(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.list_url, {'code': 'manager', 'name': 'Manager'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_ok_for_staff(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(self.list_url, {'code': 'manager', 'name': 'Manager'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Role.objects.filter(code='manager').exists())

    def test_create_rejects_duplicate_code(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(self.list_url, {'code': 'admin', 'name': 'Dup'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_rejects_non_slug_code(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(self.list_url, {'code': 'Not A Slug', 'name': 'X'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch_cannot_change_code(self):
        self.client.force_authenticate(self.staff)
        response = self.client.patch(
            self.detail_url(self.seller_role.pk), {'code': 'hacked', 'name': 'Seller X'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.seller_role.refresh_from_db()
        self.assertEqual(self.seller_role.code, 'seller')
        self.assertEqual(self.seller_role.name, 'Seller X')

    def test_delete_role_without_users(self):
        role = Role.objects.create(code='manager', name='Manager')
        self.client.force_authenticate(self.staff)
        response = self.client.delete(self.detail_url(role.pk))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_role_with_users_returns_409(self):
        self.client.force_authenticate(self.staff)
        response = self.client.delete(self.detail_url(self.customer_role.pk))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            response.data['detail'],
            'No se puede eliminar un rol con usuarios asignados.',
        )
        self.assertTrue(Role.objects.filter(code='customer').exists())
