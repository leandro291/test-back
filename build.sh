#!/usr/bin/env bash
# Render build script — https://render.com/docs/deploy-django
# Requiere DJANGO_SETTINGS_MODULE=config.settings.production en el entorno de Render.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Crea el superusuario si no existe (lee DJANGO_SUPERUSER_EMAIL/USERNAME/PASSWORD del entorno).
# El `|| true` evita que el build falle en los siguientes deploys, cuando el usuario ya existe.
python manage.py createsuperuser --noinput || true
