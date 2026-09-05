"""Test settings."""
from .base import *  # noqa: F401,F403

DEBUG = False

# El test runner de Django antepone "test_" al NAME automáticamente.

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
