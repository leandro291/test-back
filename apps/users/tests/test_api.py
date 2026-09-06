from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegisterAPITests(APITestCase):
    url = '/api/v1/auth/register/'

    def valid_payload(self, **overrides):
        payload = {
            'email': 'ana@example.com',
            'username': 'ana',
            'password': 'una-clave-segura-123',
            'password2': 'una-clave-segura-123',
            'first_name': 'Ana',
            'last_name': 'Gómez',
        }
        payload.update(overrides)
        return payload

    def test_register_with_valid_data_returns_201(self):
        response = self.client.post(self.url, self.valid_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['role'], 'customer')
        self.assertNotIn('password', response.data)
        user = User.objects.get(email='ana@example.com')
        self.assertTrue(user.check_password('una-clave-segura-123'))
        self.assertNotEqual(user.password, 'una-clave-segura-123')

    def test_register_with_mismatched_passwords_returns_400(self):
        response = self.client.post(self.url, self.valid_payload(password2='otra-clave'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password2', response.data)

    def test_register_with_weak_password_returns_400(self):
        response = self.client.post(self.url, self.valid_payload(password='123', password2='123'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_with_duplicate_email_returns_400(self):
        User.objects.create_user(username='other', email='ana@example.com', password='x')
        response = self.client.post(self.url, self.valid_payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_with_duplicate_username_returns_400(self):
        User.objects.create_user(username='ana', email='other@example.com', password='x')
        response = self.client.post(self.url, self.valid_payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginAPITests(APITestCase):
    url = '/api/v1/auth/login/'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='ana', email='ana@example.com', password='una-clave-segura-123',
        )

    def test_login_with_correct_credentials_returns_tokens(self):
        response = self.client.post(
            self.url, {'email': 'ana@example.com', 'password': 'una-clave-segura-123'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_with_wrong_password_returns_401(self):
        response = self.client.post(
            self.url, {'email': 'ana@example.com', 'password': 'wrong-password'},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_unknown_email_returns_401(self):
        response = self.client.post(
            self.url, {'email': 'nadie@example.com', 'password': 'una-clave-segura-123'},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RefreshAPITests(APITestCase):
    login_url = '/api/v1/auth/login/'
    refresh_url = '/api/v1/auth/refresh/'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='ana', email='ana@example.com', password='una-clave-segura-123',
        )

    def test_refresh_with_valid_token_returns_new_access(self):
        login_response = self.client.post(
            self.login_url, {'email': 'ana@example.com', 'password': 'una-clave-segura-123'},
        )
        original_access = login_response.data['access']
        refresh = login_response.data['refresh']

        response = self.client.post(self.refresh_url, {'refresh': refresh})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertNotEqual(response.data['access'], original_access)

    def test_refresh_with_invalid_token_returns_401(self):
        response = self.client.post(self.refresh_url, {'refresh': 'not-a-valid-token'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthEndToEndTests(APITestCase):
    register_url = '/api/v1/auth/register/'
    login_url = '/api/v1/auth/login/'
    refresh_url = '/api/v1/auth/refresh/'
    roles_url = '/api/v1/roles/'

    def test_register_login_access_protected_endpoint_and_refresh(self):
        register_payload = {
            'email': 'ana@example.com',
            'username': 'ana',
            'password': 'una-clave-segura-123',
            'password2': 'una-clave-segura-123',
        }
        register_response = self.client.post(self.register_url, register_payload)
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)

        login_response = self.client.post(
            self.login_url,
            {'email': 'ana@example.com', 'password': 'una-clave-segura-123'},
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        access = login_response.data['access']
        refresh = login_response.data['refresh']

        unauthenticated_response = self.client.get(self.roles_url)
        self.assertEqual(unauthenticated_response.status_code, status.HTTP_401_UNAUTHORIZED)

        authenticated_response = self.client.get(
            self.roles_url, HTTP_AUTHORIZATION=f'Bearer {access}',
        )
        self.assertEqual(authenticated_response.status_code, status.HTTP_200_OK)

        refresh_response = self.client.post(self.refresh_url, {'refresh': refresh})
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        new_access = refresh_response.data['access']

        renewed_response = self.client.get(
            self.roles_url, HTTP_AUTHORIZATION=f'Bearer {new_access}',
        )
        self.assertEqual(renewed_response.status_code, status.HTTP_200_OK)
