# 001 — App de dominio `roles`

**Estado:** Implementada y aprobada por el reviewer (2026-09-05) — decisión 6: permiso de escritura por `is_staff`.
**Apps afectadas:** roles (nueva), users (modificada), config

## Objetivo

Modelar los roles de negocio que un usuario puede tener en el ecommerce (`customer`, `seller`,
`admin`) como un modelo con filas, conectado a `users.User` por una FK. Expone una API para
consultarlos y una administración restringida a staff.

## Alcance

- Nueva app `apps/roles/` con `models.py`, `serializers.py`, `views.py`, `urls.py`,
  `permissions.py`, `filters.py`, `admin.py`, `apps.py`, `migrations/`, `tests/`.
- Modelo `Role` heredando de `core.BaseModel`.
- FK `role` en `users.User` apuntando a `Role`, con rol por defecto `customer`.
- Data migration que crea el set inicial de roles.
- `RoleViewSet` en `/api/v1/roles/`: lectura para autenticados, escritura solo para staff.
- Protección de borrado de un rol con usuarios asignados (respuesta 409).
- Filtros y búsqueda para el front.
- Registro en el admin de Django (`Role` + columna `role` en el `UserAdmin`).
- Tests de modelo y de permisos de endpoint.

## Fuera de alcance

- Matriz de permisos por rol (qué puede hacer cada rol en `catalog`/`orders`). Cada spec que
  necesite proteger un endpoint por rol definirá su propia regla.
- Flujo de registro/alta de usuarios (no existe todavía). La asignación del rol por defecto en el
  alta se implementará en la spec de auth de `users`; acá solo queda el default a nivel modelo.
- Múltiples roles por usuario. Se decide explícitamente **un rol por usuario**.
- Endpoint para cambiar el rol de un usuario (vive en la futura API de `users`).

## Decisiones (a revisar en la aprobación)

1. **Relación**: `User.role` es un `ForeignKey` a `Role` (`on_delete=PROTECT`,
   `related_name='users'`). Un rol por usuario, rol reutilizable. Es la lectura de "conectada
   mediante una PK".
2. **`Role` es un modelo con filas**, no `TextChoices`: el requerimiento pide admin + serializer +
   view + filtros, todo eso necesita filas administrables.
3. **`code` inmutable**: identificador programático (`user.role.code == 'admin'`). Se puede setear
   al crear, pero no editar después (read-only en update).
4. **Set inicial**: `customer` (comprador final, rol por defecto), `seller` (publica productos en
   el catálogo), `admin` (gestión de la plataforma). Alineado con las apps `catalog` y `orders`
   del SETUP.
5. **Rol por defecto**: `customer`. Se asigna vía `default=get_default_role` en el campo `role` y
   se completan los usuarios existentes en una data migration. `is_staff` / `is_superuser` no se
   tocan: siguen controlando el acceso a `/admin/` y son ortogonales al `Role` de negocio.
6. **Permiso de escritura — A CONFIRMAR**: por ahora `IsAdminOrReadOnly` se basa en
   `request.user.is_staff`. Cuando llegue la matriz de permisos de `catalog`/`orders`,
   probablemente pase a chequear `request.user.role.code == 'admin'` (el rol de negocio en vez del
   flag de Django). Se deja `is_staff` ahora porque es lo único disponible y no hay endpoint que
   dependa todavía del `code`.

## Modelos

### `Role` (nuevo) — `apps/roles/models.py`

Hereda de `apps.core.models.BaseModel` (`created_at`, `updated_at`, `ordering = ['-created_at']`).

| Campo | Tipo | Notas |
|---|---|---|
| `code` | `SlugField(max_length=32, unique=True)` | Identificador programático. Inmutable tras la creación (regla de serializer, no de BD). |
| `name` | `CharField(max_length=64)` | Nombre legible. |
| `description` | `TextField(blank=True)` | Opcional. |

- `Meta.ordering = ['name']` (override del `BaseModel` para listados alfabéticos).
- `Meta.db_table = 'roles'`.
- `__str__` devuelve `name`.
- Índices: el `unique=True` de `code` ya crea índice; no se agregan más.
- Constraints: ninguno adicional.
- Manager: `RoleQuerySet` con `with_user_count()` (`annotate(user_count=Count('users'))`),
  expuesto como `objects = RoleQuerySet.as_manager()`.
- Helper de módulo `get_default_role()`: devuelve (get_or_create) el `Role` con `code='customer'`.
  Se usa como `default` de `User.role`. No se llama en tiempo de import.
- Migración: sí (`0001_initial`).

### `User` (modificado) — `apps/users/models.py`

| Campo | Tipo | Notas |
|---|---|---|
| `role` | `FK('roles.Role', on_delete=PROTECT, related_name='users')` | Rol de negocio. `default=apps.roles.models.get_default_role`. |

- Estado final: `null=False`. Se llega en tres migraciones (ver Tareas) para poder poblar los
  usuarios ya existentes en Neon sin romper la constraint.
- No cambia `USERNAME_FIELD`, `db_table`, `ordering` ni nada más del modelo.

## Endpoints

Router DRF montado en `apps/roles/urls.py` e incluido desde `config/urls.py` bajo
`/api/v1/roles/`. Aparece en `/api/v1/docs/` por `drf-spectacular`.

### `GET /api/v1/roles/`

- **Permisos:** `IsAuthenticated`
- **Filtros:** `code` (exacto), `name` (icontains) — vía `RoleFilter`
- **Búsqueda:** `search` sobre `name`, `description`
- **Orden:** `name`, `created_at` (default `name`)
- **Respuesta 200:**

```json
{"count": 3, "results": [
  {"id": 1, "code": "admin", "name": "Administrator", "description": "", "user_count": 1,
   "created_at": "...", "updated_at": "..."}
]}
```

### `GET /api/v1/roles/{id}/`

- **Permisos:** `IsAuthenticated`
- **Respuestas:** `200` · `404` inexistente

### `POST /api/v1/roles/`

- **Permisos:** `IsAdminOrReadOnly` (requiere `is_staff`)
- **Request:** `{"code": "manager", "name": "Manager", "description": "..."}`
- **Validación:** `code` slug único; `name` requerido.
- **Respuestas:** `201` creado · `400` validación · `401` sin token · `403` autenticado sin staff

### `PUT/PATCH /api/v1/roles/{id}/`

- **Permisos:** `IsAdminOrReadOnly`
- **Request:** `{"name": "...", "description": "..."}` — `code` es read-only, se ignora si se envía.
- **Respuestas:** `200` · `400` · `403` · `404`

### `DELETE /api/v1/roles/{id}/`

- **Permisos:** `IsAdminOrReadOnly`
- **Comportamiento:** si el rol tiene usuarios asignados, `on_delete=PROTECT` lanza
  `ProtectedError`; el `ViewSet` la captura y devuelve `409 Conflict` con
  `{"detail": "No se puede eliminar un rol con usuarios asignados."}`.
- **Respuestas:** `204` sin usuarios · `409` con usuarios · `403` · `404`

## Tareas

Ordenadas por dependencia. Cada una acotada a un archivo o una app.

1. Crear el esqueleto de `apps/roles/`: `__init__.py`, `apps.py` (`RolesConfig`,
   `name = 'apps.roles'`, `default_auto_field = 'django.db.models.BigAutoField'`),
   `migrations/__init__.py`.
2. Registrar `'apps.roles'` en `INSTALLED_APPS` de `config/settings/base.py`, después de
   `'apps.users'`.
3. `apps/roles/models.py`: `RoleQuerySet` (`with_user_count()`), `Role` (campos, `Meta`,
   `__str__`) y `get_default_role()`.
4. Generar `apps/roles/migrations/0001_initial.py` (`makemigrations roles`) y revisarla.
5. `apps/roles/migrations/0002_seed_roles.py`: data migration `RunPython` que hace
   `get_or_create` de `customer`, `seller`, `admin` con sus `name`/`description`. Reverse: borra
   esos tres `code`. Idempotente.
6. `apps/users/models.py`: agregar `role = FK('roles.Role', on_delete=PROTECT,
   related_name='users', null=True, default=get_default_role)` (import de
   `apps.roles.models.get_default_role`).
7. `apps/users/migrations/0002_user_role.py` (`makemigrations users`) — `AddField` con
   `null=True`. Depende de `roles.0002_seed_roles`.
8. `apps/users/migrations/0003_assign_default_role.py`: data migration que setea el rol
   `customer` a todos los `User` con `role__isnull=True`. Reverse: `no-op`.
9. `apps/users/models.py` + `apps/users/migrations/0004_user_role_required.py`: quitar `null=True`
   del campo y generar el `AlterField` a `null=False`.
10. `apps/roles/serializers.py`: `RoleSerializer` (lectura + create; expone `user_count` de la
    anotación o vía `SerializerMethodField`; valida `code` como slug único) y `RoleUpdateSerializer`
    (hereda del anterior, `code` en `read_only_fields`).
11. `apps/roles/permissions.py`: `IsAdminOrReadOnly` — `SAFE_METHODS` para cualquier autenticado,
    métodos de escritura solo si `request.user.is_staff`.
12. `apps/roles/filters.py`: `RoleFilter` (`FilterSet`) con `code` (exacto) y `name` (icontains).
13. `apps/roles/views.py`: `RoleViewSet(ModelViewSet)` — `queryset =
    Role.objects.with_user_count()`, `permission_classes = [IsAuthenticated, IsAdminOrReadOnly]`,
    `filterset_class`, `search_fields = ['name', 'description']`,
    `ordering_fields = ['name', 'created_at']`, `get_serializer_class()` (update →
    `RoleUpdateSerializer`), y override de `destroy()` que captura `django.db.models.ProtectedError`
    y devuelve `409`.
14. `apps/roles/urls.py`: `DefaultRouter` registrando `RoleViewSet` como `roles`. Incluirlo en
    `config/urls.py`: `path('api/v1/', include('apps.roles.urls'))`.
15. `apps/roles/admin.py`: `RoleAdmin` (`list_display = ('code', 'name', 'user_count')`,
    `search_fields = ('code', 'name')`, `readonly_fields` para `code` en edición). Definir
    `user_count` con `get_queryset` anotado.
16. `apps/users/admin.py`: reemplazar el `register(User, UserAdmin)` plano por un `UserAdmin`
    custom que agregue `role` a `list_display`, `list_filter` y a un `fieldset`.
17. `apps/roles/tests/`: `__init__.py`, `test_models.py` (unicidad de `code`, `__str__`,
    `get_default_role` idempotente, `with_user_count`), `test_api.py` (matriz de permisos y
    casos de error, ver criterios de aceptación).

## Criterios de aceptación

- [ ] `python manage.py check` pasa sin errores.
- [ ] `python manage.py makemigrations --check --dry-run` no reporta migraciones faltantes.
- [ ] `python manage.py migrate` aplica limpio sobre una base vacía y sobre la base actual (con
      usuarios ya existentes) sin violar la constraint `NOT NULL` de `users.role`.
- [ ] Tras migrar, existen exactamente los roles `customer`, `seller`, `admin` y todo `User`
      existente tiene `role = customer`.
- [ ] Volver a correr `migrate` (o revertir y reaplicar `0002_seed_roles`) no duplica roles.
- [ ] `GET /api/v1/roles/` sin token devuelve `401`.
- [ ] `GET /api/v1/roles/` con token de usuario no-staff devuelve `200` y pagina.
- [ ] `?code=admin` devuelve solo el rol `admin`; `?name=sell` (icontains) devuelve `seller`.
- [ ] `search=` sobre una palabra de la `description` filtra el listado.
- [ ] `POST /api/v1/roles/` sin token → `401`; con token no-staff → `403`; con token staff y body
      válido → `201`.
- [ ] `POST` con `code` duplicado o con espacios/mayúsculas (no-slug) → `400`.
- [ ] `PATCH` de un rol cambiando `code` no modifica el `code` almacenado (queda igual), `200`.
- [ ] `DELETE` de un rol sin usuarios (staff) → `204`.
- [ ] `DELETE` del rol `customer` (con usuarios asignados) → `409` con el `detail` esperado, y el
      rol sigue existiendo.
- [ ] El listado no dispara N+1 para `user_count`: se resuelve con `annotate`, no por fila.
- [ ] `RoleViewSet` aparece en `/api/v1/docs/`.
- [ ] En `/admin/`, la lista de usuarios muestra la columna `role` y permite filtrar por ella.
- [ ] `apps/roles/tests/` pasa completo con `python manage.py test apps.roles`.
