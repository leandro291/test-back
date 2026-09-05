#!/usr/bin/env bash
# Render build script — https://render.com/docs/deploy-django
# Requiere DJANGO_SETTINGS_MODULE=config.settings.production en el entorno de Render.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
