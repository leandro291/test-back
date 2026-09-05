# Backend Ecommerce

API REST de un ecommerce personal, en Django + Django REST Framework. Este archivo es el mapa del
proyecto: qué hay, dónde está y cómo se accede a cada parte.

- **Cómo instalar y correr** → [`SETUP.md`](SETUP.md)
- **Stack, fuentes de verdad y metodología de trabajo (SDD)** → [`claude.md`](claude.md)
- **Qué se construyó y por qué, tarea por tarea** → [`specs/`](specs/)

---

## Arquitectura

```
config/            # proyecto Django
├── settings/      # base · development · production · test
└── urls.py        # monta cada app bajo /api/v1/ + admin + docs

apps/
├── core/          # BaseModel (timestamps + soft delete), permisos compartidos
├── users/         # User custom (login por email), rol asignado por FK
├── roles/         # Role de negocio (customer, seller, admin) — CRUD
└── catalog/       # Category y Product — CRUD público
```

Cada app expone su `urls.py` (router de DRF) y se incluye desde `config/urls.py`. Detalle de la
estructura interna de una app y dónde va cada archivo: [`SETUP.md`](SETUP.md) §2.

**Soft delete:** todos los modelos heredan de `apps.core.BaseModel`. `delete()` marca `deleted_at`
en vez de borrar la fila. `Model.objects` oculta las borradas; `Model.all_objects` las incluye.

---

## Cómo acceder a cada parte

| Parte | URL (local) | Acceso |
|---|---|---|
| Admin de Django | `http://localhost:8000/admin/` | superusuario |
| API v1 | `http://localhost:8000/api/v1/` | ver tabla de endpoints |
| Swagger UI | `http://localhost:8000/api/v1/docs/` | público |
| Esquema OpenAPI | `http://localhost:8000/api/v1/schema/` | público |

### Endpoints

Todos bajo `/api/v1/`. Paginados (`PAGE_SIZE=20`), con `?search=`, `?ordering=` y filtros de
`django-filter`. Autenticación por JWT (`Authorization: Bearer <token>`).

| Recurso | Endpoint | Lectura | Escritura (POST/PUT/PATCH/DELETE) |
|---|---|---|---|
| Roles | `roles/`, `roles/{id}/` | usuario autenticado | staff |
| Categorías | `categories/`, `categories/{id}/` | pública | staff |
| Productos | `products/`, `products/{id}/` | pública | staff |

- Permiso compartido: `apps.core.permissions.IsAdminOrReadOnly`.
- Lectura pública (categorías, productos) devuelve solo lo visible; el staff ve también lo inactivo
  y lo soft-deleted.
- `DELETE` de un rol con usuarios, o de una categoría con productos → `409 Conflict`.

> **Auth:** el modelo `User` y los roles ya existen, pero los endpoints de registro / obtención de
> token JWT todavía no están montados en `config/urls.py`. Hasta entonces, para probar endpoints
> autenticados se usa un token generado a mano o la sesión del admin.

---

## Tests

```bash
python manage.py test --settings=config.settings.test
```

Los tests viven en `apps/<app>/tests/`.

---

## Deploy

Render, con `build.sh` como Build Command y `gunicorn config.wsgi:application` como Start Command.
Pasos y variables de entorno: [`SETUP.md`](SETUP.md) §6.
