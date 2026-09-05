# 002 — App de dominio `catalog`: modelo `Category`

**Estado:** Implementada y aprobada por el reviewer (2026-09-05) — decisiones 1 (plana), 3 (lectura pública) y 4 (permiso a `core`) confirmadas.
**Apps afectadas:** catalog (nueva), core (modificada), roles (modificada — solo import), config

## Objetivo

Inaugurar la app `catalog` con el modelo `Category`: categorías planas para clasificar los
productos del ecommerce. Expone un CRUD REST (lectura pública, escritura para staff), filtros y
búsqueda para el front, y un apartado en el admin de Django para gestionarlas.

## Alcance

- Nueva app `apps/catalog/` con `__init__.py`, `apps.py`, `models.py`, `serializers.py`,
  `views.py`, `urls.py`, `filters.py`, `admin.py`, `migrations/`, `tests/`.
- Modelo `Category` heredando de `apps.core.models.BaseModel`.
- `CategoryQuerySet.active()` expuesto como `objects = CategoryQuerySet.as_manager()`.
- `CategoryViewSet` en `/api/v1/categories/`: lectura `AllowAny`, escritura solo staff.
- `slug` autogenerado desde `name` en `Model.save()`, editable por staff.
- Filtros (`name`, `is_active`), búsqueda y ordenamiento.
- Mover `IsAdminOrReadOnly` de `apps/roles/permissions.py` a `apps/core/permissions.py` (permiso
  compartido) y reapuntar el import de `roles`.
- Registro en el admin de Django (`CategoryAdmin`).
- Tests de modelo y de matriz de permisos del endpoint.

## Fuera de alcance

- `Product` y `ProductImage`, y la relación `Category ↔ Product` (FK inversa, `on_delete=PROTECT`,
  respuesta 409 al borrar una categoría con productos). Todo eso lo define la spec de `Product`.
  En esta spec el `DELETE` de una categoría es **borrado físico y siempre procede**.
- Jerarquía / subcategorías (`parent` self-FK). Ver decisión 1.
- Imágenes de categoría (el SETUP reserva imágenes para `Product`/`ProductImage`).
- Reordenamiento manual de categorías (sin campo de orden — YAGNI).
- Cambiar el permiso de escritura a `request.user.role.code == 'admin'` (misma deuda anotada en
  `001-roles`, decisión 6: hoy se usa `is_staff`).

## Decisiones (a confirmar en la aprobación)

1. **Jerarquía**: `Category` **plana**, sin `parent`. Si más adelante se necesita árbol, otra spec
   agrega un self-FK nullable (migración barata). El usuario puede pedir `parent` desde ya — si es
   así, se ajusta esta spec antes de implementar.
2. **`slug`**: `SlugField(max_length=120, unique=True)`. Se autogenera con
   `django.utils.text.slugify(name)` en `Category.save()` cuando llega vacío. **Editable** por
   staff (a diferencia del `code` inmutable de `Role`: un slug de categoría puede necesitar
   corrección). El lookup de la URL es por `id` (consistencia con `roles`); el `slug` se expone en
   el serializer para SEO del front pero no es el lookup.
   - Ceiling: si dos `name` distintos colapsan al mismo slug (`"Café"` / `"Cafe"`), el segundo
     `save()` levanta `IntegrityError` → `400`. Se acepta; el staff corrige el slug a mano.
3. **Lectura pública**: `GET /api/v1/categories/` y el detalle son `AllowAny` (el catálogo es
   público según el SETUP). Se aparta deliberadamente de `001-roles` (que pedía `IsAuthenticated`
   para GET). Escritura (`POST/PUT/PATCH/DELETE`): staff.
4. **Permiso compartido**: se **mueve** `IsAdminOrReadOnly` a `apps/core/permissions.py` — el
   SETUP define `core` como hogar de "permisos y paginación comunes". `roles` y `catalog` lo
   importan de ahí. Esto toca código de `001-roles` (aprobado), pero es un cambio **solo de
   import, sin cambio de comportamiento**: la clase es idéntica y ya hace exactamente lo que
   `catalog` necesita (`SAFE_METHODS` → `True` para cualquiera, incluido anónimo; escritura solo
   `is_staff`). El `IsAuthenticated` que `roles` suma en `permission_classes` es lo que mantiene su
   lectura privada; `catalog` no lo agrega y su lectura queda pública.
5. **`is_active`**: `BooleanField(default=True)`. El listado y el detalle para usuarios anónimos y
   no-staff devuelven **solo** `is_active=True` (vía `get_queryset()` → `.active()`). Staff ve
   todas y puede filtrar por `?is_active=`. No hay soft delete: ocultar = `is_active=False`,
   borrar = `DELETE` físico. Pedir el detalle de una categoría inactiva siendo anónimo → `404`.
6. **Permiso de escritura**: `is_staff` (consistente con `001-roles`, decisión 6).

## Modelos

### `Category` (nuevo) — `apps/catalog/models.py`

Hereda de `apps.core.models.BaseModel` (`created_at`, `updated_at`).

| Campo | Tipo | Notas |
|---|---|---|
| `name` | `CharField(max_length=100, unique=True)` | Nombre legible. Requerido. |
| `slug` | `SlugField(max_length=120, unique=True, blank=True)` | Autogenerado desde `name` en `save()` si llega vacío. Editable por staff. |
| `description` | `TextField(blank=True)` | Opcional. |
| `is_active` | `BooleanField(default=True)` | Visibilidad pública. |

- `Meta.db_table = 'categories'`.
- `Meta.ordering = ['name']` (override del `BaseModel`, listados alfabéticos).
- `__str__` devuelve `name`.
- Índices: los `unique=True` de `name` y `slug` ya crean índice; no se agregan más.
- Constraints: ninguno adicional.
- `save()`: `if not self.slug: self.slug = slugify(self.name)`, luego `super().save()`.
- Manager: `CategoryQuerySet` con `.active()` (`filter(is_active=True)`), expuesto como
  `objects = CategoryQuerySet.as_manager()`.
- Migración: sí (`0001_initial`). Sin data migration (no hay set inicial de categorías).

## Permisos

### `IsAdminOrReadOnly` — `apps/core/permissions.py` (movido desde `apps/roles/permissions.py`)

Sin cambios de lógica respecto de `001-roles`:

- `request.method in SAFE_METHODS` → `True`.
- Métodos de escritura → `bool(request.user and request.user.is_staff)`.

`apps/roles/views.py` pasa a importarlo de `apps.core.permissions`. Se elimina
`apps/roles/permissions.py`.

## Endpoints

Router DRF montado en `apps/catalog/urls.py` e incluido desde `config/urls.py` bajo
`/api/v1/categories/`. Aparece en `/api/v1/docs/` por `drf-spectacular`.

### `GET /api/v1/categories/`

- **Permisos:** `AllowAny`
- **QuerySet:** anónimo / no-staff → solo `is_active=True`; staff → todas.
- **Filtros:** `name` (icontains), `is_active` (exacto) — vía `CategoryFilter`.
- **Búsqueda:** `search` sobre `name`, `description`.
- **Orden:** `name`, `created_at` (default `name`).
- **Respuesta 200:**

```json
{"count": 2, "results": [
  {"id": 1, "name": "Beverages", "slug": "beverages", "description": "",
   "is_active": true, "created_at": "...", "updated_at": "..."}
]}
```

### `GET /api/v1/categories/{id}/`

- **Permisos:** `AllowAny`
- **Respuestas:** `200` · `404` inexistente o inactiva pedida por anónimo/no-staff.

### `POST /api/v1/categories/`

- **Permisos:** `IsAdminOrReadOnly` (requiere `is_staff`).
- **Request:** `{"name": "Beverages", "description": "...", "slug": "beverages", "is_active": true}`
  — `slug` opcional (se autogenera desde `name`); `is_active` opcional (default `true`).
- **Validación:** `name` requerido y único; `slug` único si se envía.
- **Respuestas:** `201` creado · `400` validación · `403` autenticado sin staff · `401` sin token.

### `PUT/PATCH /api/v1/categories/{id}/`

- **Permisos:** `IsAdminOrReadOnly`.
- **Request:** cualquier subconjunto de `name`, `slug`, `description`, `is_active`. `slug` es
  editable.
- **Respuestas:** `200` · `400` · `403` · `404`.

### `DELETE /api/v1/categories/{id}/`

- **Permisos:** `IsAdminOrReadOnly`.
- **Comportamiento:** borrado físico, siempre procede (no hay FK entrante todavía).
- **Respuestas:** `204` · `403` · `404`.

## Serializers

### `CategorySerializer` — `apps/catalog/serializers.py`

- `ModelSerializer` sobre `Category`.
- `fields = ['id', 'name', 'slug', 'description', 'is_active', 'created_at', 'updated_at']`.
- `read_only_fields = ['id', 'created_at', 'updated_at']`.
- `extra_kwargs = {'slug': {'required': False}}` — opcional en create y update; el `save()` del
  modelo lo completa si viene vacío. La unicidad de `name`/`slug` la valida el `UniqueValidator`
  que DRF deriva del modelo.
- No hace falta un serializer de escritura aparte: no hay campos inmutables (a diferencia del
  `code` de `Role`).

## Filtros

### `CategoryFilter` — `apps/catalog/filters.py`

- `FilterSet` sobre `Category`.
- `name`: `CharFilter(lookup_expr='icontains')`.
- `is_active`: filtro exacto (efectivo solo para staff; para anónimo el queryset ya está acotado).
- `Meta.fields = ['name', 'is_active']`.

## Vistas

### `CategoryViewSet` — `apps/catalog/views.py`

- `ModelViewSet`.
- `serializer_class = CategorySerializer`.
- `permission_classes = [IsAdminOrReadOnly]` (sin `IsAuthenticated`: lectura pública).
- `filterset_class = CategoryFilter`.
- `search_fields = ['name', 'description']`.
- `ordering_fields = ['name', 'created_at']`, `ordering = ['name']`.
- `get_queryset()`: base `Category.objects.all()`; si
  `not (self.request.user and self.request.user.is_staff)` → `.active()`.

## Admin

### `CategoryAdmin` — `apps/catalog/admin.py`

- `@admin.register(Category)`.
- `list_display = ('name', 'slug', 'is_active')`.
- `list_filter = ('is_active',)`.
- `search_fields = ('name',)`.
- `prepopulated_fields = {'slug': ('name',)}`.

## Tareas

Ordenadas por dependencia. Cada una acotada a un archivo o una app.

1. Crear el esqueleto de `apps/catalog/`: `__init__.py`, `apps.py` (`CatalogConfig`,
   `name = 'apps.catalog'`, `default_auto_field = 'django.db.models.BigAutoField'`),
   `migrations/__init__.py`.
2. Registrar `'apps.catalog'` en `INSTALLED_APPS` de `config/settings/base.py`, después de
   `'apps.roles'`.
3. Crear `apps/core/permissions.py` con `IsAdminOrReadOnly` (copiado tal cual de
   `apps/roles/permissions.py`). Actualizar el import en `apps/roles/views.py` a
   `from apps.core.permissions import IsAdminOrReadOnly`. Eliminar `apps/roles/permissions.py`.
4. `apps/catalog/models.py`: `CategoryQuerySet` (`.active()`), `Category` (campos, `Meta`,
   `__str__`, `save()` con `slugify`), `objects = CategoryQuerySet.as_manager()`.
5. Generar `apps/catalog/migrations/0001_initial.py` (`makemigrations catalog`) y revisarla.
6. `apps/catalog/serializers.py`: `CategorySerializer`.
7. `apps/catalog/filters.py`: `CategoryFilter`.
8. `apps/catalog/views.py`: `CategoryViewSet` con `get_queryset()` que acota a `.active()` para
   no-staff.
9. `apps/catalog/urls.py`: `DefaultRouter` registrando `CategoryViewSet` como `categories`
   (`basename='category'`). Incluirlo en `config/urls.py`:
   `path('api/v1/', include('apps.catalog.urls'))`.
10. `apps/catalog/admin.py`: `CategoryAdmin`.
11. `apps/catalog/tests/`: `__init__.py`, `test_models.py` (autogeneración de slug, unicidad de
    `name`/`slug`, `__str__`, `.active()`), `test_api.py` (matriz de permisos, filtros, búsqueda,
    404 de inactiva para anónimo, ver criterios de aceptación).

## Criterios de aceptación

- [ ] `python manage.py check` pasa sin errores.
- [ ] `python manage.py makemigrations --check --dry-run` no reporta migraciones faltantes.
- [ ] `python manage.py migrate` aplica limpio sobre una base vacía y sobre la base actual.
- [ ] `python manage.py test apps.roles` sigue pasando completo (el import movido no rompe nada).
- [ ] `GET /api/v1/categories/` sin token devuelve `200` y pagina (`count` + `results`).
- [ ] Un anónimo no ve categorías con `is_active=False` en el listado; pedir su detalle → `404`.
- [ ] Un staff autenticado ve las categorías inactivas y `?is_active=false` las filtra.
- [ ] `?name=bev` (icontains) devuelve solo las categorías cuyo nombre contiene "bev".
- [ ] `search=` sobre una palabra de la `description` filtra el listado.
- [ ] `POST /api/v1/categories/` sin token → `401`; con token no-staff → `403`; con token staff y
      `{"name": "Beverages"}` → `201` y el `slug` queda `"beverages"`.
- [ ] `POST` con `name` duplicado → `400`. `POST` con `slug` duplicado → `400`.
- [ ] `PATCH` de una categoría cambiando `slug` a un valor válido y libre → `200` y persiste.
- [ ] `PATCH` con token no-staff → `403`.
- [ ] `DELETE` de una categoría (staff) → `204` y deja de existir.
- [ ] `CategoryViewSet` aparece en `/api/v1/docs/`.
- [ ] En `/admin/`, el listado de categorías muestra `name`, `slug`, `is_active`, permite filtrar
      por `is_active` y `slug` se autocompleta desde `name` al tipear.
- [ ] `apps/catalog/tests/` pasa completo con `python manage.py test apps.catalog`.
