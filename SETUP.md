# SETUP — Arquitectura e instalación

Fuente de verdad de la **estructura de carpetas**, las **dependencias** y las **variables de
entorno** del proyecto. Todo archivo nuevo se ubica según este documento.

Los patrones de código (cómo se escribe un settings, un modelo, un ViewSet) no están acá: están en
la skill `django-patterns`. Este documento define *dónde*, la skill define *cómo*.

---

## 1. Requisitos previos

| Requisito | Versión |
|---|---|
| Python | 3.12+ |
| PostgreSQL | 14+ corriendo local o accesible por red |
| pip / venv | incluidos en Python |

---

## 2. Arquitectura

```
test-back/
├── claude.md                    # punto de entrada del proyecto
├── SETUP.md                     # este archivo
├── manage.py
├── requirements.txt
├── .env.example                 # claves requeridas, sin valores
├── .gitignore
├── .claude/
│   └── agents/                  # orquestador, spec, developer, reviewer
├── specs/                       # NNN-nombre.md — una por funcionalidad
├── config/
│   ├── settings/
│   │   ├── base.py              # común a todos los entornos
│   │   ├── development.py       # DEBUG, hosts locales
│   │   ├── production.py        # seguridad, SSL, HSTS, logging
│   │   └── test.py              # BD de test
│   ├── urls.py                  # incluye los urls.py de cada app bajo /api/v1/
│   ├── wsgi.py
│   └── asgi.py
└── apps/
    ├── core/                    # BaseModel, permisos y paginación compartidos
    ├── users/                   # User custom, auth JWT, admin
    ├── catalog/                 # Category, Product, ProductImage
    └── orders/                  # Cart, CartItem, Order, OrderItem
```

### Apps de dominio

| App | Modelos | Responsabilidad |
|---|---|---|
| `core` | `BaseModel` (`created_at`, `updated_at`) | Piezas compartidas: modelo base, permisos y paginación comunes. Sin lógica de negocio propia. |
| `users` | `User` (`AbstractUser`, `email` como `USERNAME_FIELD`) | Registro, login JWT, perfil, admin. |
| `catalog` | `Category`, `Product`, `ProductImage` | Catálogo público. Imágenes en Cloudinary. Filtros y búsqueda. |
| `orders` | `Cart`, `CartItem`, `Order`, `OrderItem` | Carrito y órdenes. Transiciones de estado en `services.py`. |

### Archivos dentro de cada app

```
apps/<app>/
├── models.py
├── serializers.py
├── views.py
├── urls.py
├── permissions.py       # clases de permiso
├── filters.py           # FilterSet de django-filter
├── services.py          # lógica de negocio multi-modelo
├── admin.py
├── apps.py
├── migrations/
└── tests/
```

Se crean **cuando la spec los necesita**, no de entrada. Una app sin lógica multi-modelo no lleva
`services.py`; una sin filtros no lleva `filters.py`.

---

## 3. Dependencias

`requirements.txt`:

```
Django
djangorestframework
djangorestframework-simplejwt
django-cors-headers
django-filter
cloudinary
django-cloudinary-storage
psycopg[binary]
django-environ
drf-spectacular
Pillow
gunicorn
whitenoise[brotli]
```

| Paquete | Rol |
|---|---|
| `Django` | Framework, ORM, admin |
| `djangorestframework` | Serializers, ViewSets, routers, permisos |
| `djangorestframework-simplejwt` | Tokens de acceso y refresh |
| `django-cors-headers` | Cabeceras CORS para los frontends autorizados |
| `django-filter` | `FilterSet` conectados al `DjangoFilterBackend` |
| `cloudinary` + `django-cloudinary-storage` | Subida y almacenamiento de imágenes de producto |
| `psycopg[binary]` | Driver PostgreSQL |
| `django-environ` | Lectura de `.env` y casting de tipos |
| `drf-spectacular` | Esquema OpenAPI 3 y UI Swagger en `/api/v1/docs/` |
| `Pillow` | Validación de imágenes en `ImageField` |
| `gunicorn` | Servidor WSGI en producción (Render) |
| `whitenoise[brotli]` | Servir estáticos del admin/DRF en producción sin CDN |

Agregar una dependencia fuera de esta lista requiere que una spec lo justifique.

---

## 4. Variables de entorno

`.env.example` (copiar a `.env` y completar):

```
# Django
DJANGO_SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL (Neon) — connection string completa, incluyendo ?sslmode=require
DATABASE_URL=

# Cloudinary
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

`.env` va en `.gitignore`. `.env.example` se versiona y se actualiza cada vez que se agrega una
variable nueva.

---

## 5. Instalación

```bash
# 1. Entorno virtual
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Dependencias
pip install -r requirements.txt

# 3. Base de datos
# Crear el proyecto en Neon (https://neon.tech) y copiar la connection string.

# 4. Configuración
cp .env.example .env              # pegar DATABASE_URL y completar el resto

# 5. Migraciones
python manage.py migrate

# 6. Usuario admin
python manage.py createsuperuser

# 7. Servidor
python manage.py runserver
```

Admin en `http://localhost:8000/admin/`, API en `http://localhost:8000/api/v1/`, docs Swagger en
`http://localhost:8000/api/v1/docs/` (esquema OpenAPI en `/api/v1/schema/`).

`DJANGO_SETTINGS_MODULE` por defecto en local: `config.settings.development` (definido en
`manage.py` y `config/wsgi.py`).

---

## 6. Deploy en producción (Render)

Guía oficial: <https://render.com/docs/deploy-django>.

- `build.sh` (raíz, ejecutable): `pip install` + `collectstatic` + `migrate`. Es el *Build Command*.
- *Start Command*: `gunicorn config.wsgi:application`.
- `render.yaml` (raíz): Blueprint opcional con el servicio web y las variables. Si se configura a
  mano en el dashboard, alcanza con el Build y Start Command de arriba.
- `config/settings/production.py`: `DEBUG=False`, SSL/HSTS/cookies seguras, WhiteNoise para los
  estáticos, y `RENDER_EXTERNAL_HOSTNAME` sumado a `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`.

Variables a cargar en Render (además de las que Render inyecta: `RENDER`, `RENDER_EXTERNAL_HOSTNAME`):

```
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=            # generar uno nuevo, sin el prefijo django-insecure-
DATABASE_URL=                 # connection string de Neon (o de una BD de Render)
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
CORS_ALLOWED_ORIGINS=         # URL(s) del frontend
```

`migrate` corre en cada deploy dentro de `build.sh`.

---

## 7. Convenciones

- Todas las apps viven bajo `apps/` y se registran como `apps.<nombre>` en `INSTALLED_APPS`.
- Cada app expone su `urls.py`, incluido desde `config/urls.py` bajo `/api/v1/`.
- `AUTH_USER_MODEL = 'users.User'` debe estar definido **antes de la primera migración**. Cambiarlo
  después obliga a rehacer la base.
- Una migración por cambio de modelo, generada en la misma tarea que lo introduce.
- Las imágenes se guardan en Cloudinary, nunca en el filesystem del servidor.
