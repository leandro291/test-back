# 003 — Borrado lógico (soft delete) en `core`

**Estado:** Implementada y aprobada por el reviewer (2026-09-05) — decisiones 1 (retrofit ahora), 2 (constraints parciales), 3 (`objects` filtrado + `all_objects`), 4 (restore REST fuera de alcance) confirmadas.
**Apps afectadas:** core (modificada), roles (modificada), catalog (modificada)

## Objetivo

Dar a todos los modelos que heredan de `apps.core.models.BaseModel` la capacidad de borrarse
lógicamente: `DELETE` marca la fila con una fecha en vez de eliminarla de PostgreSQL. Los datos
quedan recuperables desde el admin y la base nunca pierde información por una operación de la API.

## Decisiones que el usuario DEBE confirmar antes de implementar

1. **Scope del retrofit.** Esta spec aplica soft delete **ya** a `Role` y `Category`, lo que
   implica: cambio de contrato del `DELETE` de ambos endpoints (sigue `204`/`409` pero la fila no
   desaparece), migraciones que tocan sus índices únicos, y actualización de sus tests.
   - Alternativa si se considera demasiado: dejar solo la capacidad en `BaseModel` y que la
     adopten los modelos nuevos (`Product` en adelante), manteniendo `Role`/`Category` con borrado
     físico. Con esta alternativa se recortan las tareas 6–14 y sus criterios.
2. **Constraints únicos parciales.** Esta spec migra `Category.name`, `Category.slug` y `Role.code`
   de `unique=True` a `UniqueConstraint` con `condition=Q(deleted_at__isnull=True)`: permite volver
   a crear una "Beverages" después de soft-deletear la anterior.
   - Alternativa: mantener `unique=True` simple. Consecuencia: un `code`/`name`/`slug` de una fila
     borrada no se puede reusar hasta hacer `restore` o `hard_delete`.
3. **Manager por defecto.** `objects` pasa a **excluir** los borrados; se agrega `all_objects` que
   los ve. Contra a aceptar: `dumpdata` y cualquier acceso que use el manager por defecto (no las
   relaciones inversas — ver nota de `base_manager_name` en Modelos) dejan de ver los borrados
   salvo que se pida `all_objects` explícitamente.
4. **Endpoint REST de restore.** Queda **fuera de alcance**. El restore se hace solo desde el
   admin de Django. Se agrega `POST /{id}/restore/` cuando un frontend lo pida.

## Alcance

- `deleted_at` en `BaseModel` (campo nuevo, abstracto) + `SoftDeleteQuerySet`, `SoftDeleteManager`
  y los métodos `delete()` / `hard_delete()` / `restore()` en `BaseModel`.
- Retrofit de `Role` y `Category`: sus `QuerySet` heredan de `SoftDeleteQuerySet`, sus managers
  pasan a ser el filtrado + `all_objects`, y sus únicos pasan a `UniqueConstraint` parcial.
- Migraciones (`roles`, `catalog`) para el campo y el swap de índices. Reversibles.
- Ajuste del `destroy()` de `RoleViewSet`: guard explícito por `users.exists()` en vez de capturar
  `ProtectedError` (el soft delete ya no dispara `PROTECT`).
- Ajuste de los serializers de `Role` y `Category` para validar unicidad contra filas vivas.
- Admin de `Role` y `Category`: ven las filas borradas, muestran `deleted_at` y tienen acción
  `restore`.
- Tests: `apps/core/tests/` para el comportamiento del mixin; actualización de los tests de
  `roles` y `catalog`.

## Fuera de alcance

- `User`: no hereda de `BaseModel` y no se le agrega `deleted_at`. Para desactivar cuentas se usa
  `AbstractUser.is_active`.
- Cascada de soft delete a relaciones. Cuando exista `Product`, soft-deletear una `Category` **no**
  soft-deletea sus productos; esa regla la define la spec de `Product`.
- Endpoint REST `POST /{id}/restore/` (decisión 4).
- Purga automática / política de retención (borrar de verdad lo que lleva N días soft-deleted).
- `apps/core/permissions.py` y la paginación: no se tocan.

## Modelos

### `BaseModel` (modificado) — `apps/core/models.py`

Campo nuevo:

| Campo | Tipo | Notas |
|---|---|---|
| `deleted_at` | `DateTimeField(null=True, blank=True, db_index=True)` | `NULL` = vivo. Con fecha = borrado lógicamente. Elegido sobre un bool `is_deleted`: audita *cuándo* y no hay dos campos que puedan contradecirse. |

`SoftDeleteQuerySet(models.QuerySet)`:

- `alive()` → `filter(deleted_at__isnull=True)`
- `dead()` → `filter(deleted_at__isnull=False)`
- `delete()` → **override**: `update(deleted_at=timezone.now())`. No borra filas. Devuelve la
  cantidad afectada con la misma forma `(n, {})` que espera el llamador de un `QuerySet.delete()`.
- `hard_delete()` → `super().delete()` (borrado físico real, con cascada normal de Django).

`SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet))`:

- `get_queryset()` → `super().get_queryset().alive()`. El manager por defecto **no ve** los borrados.

`BaseModel`:

- `objects = SoftDeleteManager()` — solo vivos. Declarado **primero** → es el `default_manager`.
- `all_objects = SoftDeleteQuerySet.as_manager()` — todo, incluidos los borrados.
- `class Meta`: `abstract = True`, `ordering = ['-created_at']`, y **`base_manager_name = 'all_objects'`**.
  Sin esto, `_base_manager` sería el filtrado y un acceso a una relación (`user.role`) cuyo destino
  fue soft-deleted rompería con `DoesNotExist`. Con `all_objects` como base manager, las relaciones
  siguen resolviendo.
- `delete(self, using=None, keep_parents=False)` → **override**: `self.deleted_at = timezone.now();
  self.save(update_fields=['deleted_at'])`. **No** llama a `super().delete()`.
- `hard_delete(self, using=None, keep_parents=False)` → `super().delete(...)`.
- `restore(self)` → `self.deleted_at = None; self.save(update_fields=['deleted_at'])`.

> Nota para el `developer` (vía `django-patterns`): `SoftDeleteQuerySet.as_manager()` y
> `from_queryset(...)().` traen `use_in_migrations = False`, así que los managers no generan ruido
> en `makemigrations`.

### `Role` (modificado) — `apps/roles/models.py`

- `RoleQuerySet` pasa a heredar de `apps.core.models.SoftDeleteQuerySet` (no de `models.QuerySet`),
  para que `.with_user_count()` componga con `.alive()` / `.dead()`.
- Managers:
  - `objects = SoftDeleteManager.from_queryset(RoleQuerySet)()` — vivos + `with_user_count()`.
  - `all_objects = RoleQuerySet.as_manager()` — todo.
- `code`: se quita `unique=True` del campo y se agrega a `Meta`:
  `constraints = [UniqueConstraint(fields=['code'], condition=Q(deleted_at__isnull=True),
  name='uniq_role_code_alive')]` (decisión 2).
- `class Meta(BaseModel.Meta)`: hereda `base_manager_name`; mantiene `db_table = 'roles'` y
  `ordering = ['name']`.
- `get_default_role()`: pasa a usar `Role.all_objects.get_or_create(code='customer', ...)`. Si el
  `Role` encontrado está soft-deleted, lo restaura antes de devolver su `pk` (una fila `customer`
  borrada no debe generar un duplicado ni quedar como default muerto). Se mantiene el `try/except
  (OperationalError, ProgrammingError)` actual.

### `Category` (modificado) — `apps/catalog/models.py`

- `CategoryQuerySet` pasa a heredar de `SoftDeleteQuerySet`. `.active()` sigue igual
  (`filter(is_active=True)`) y ahora compone sobre el queryset ya filtrado por `alive()`.
- Managers:
  - `objects = SoftDeleteManager.from_queryset(CategoryQuerySet)()` — vivos + `.active()`.
  - `all_objects = CategoryQuerySet.as_manager()` — todo.
- `name` y `slug`: se quita `unique=True`; se agregan dos `UniqueConstraint` parciales en `Meta`
  (`uniq_category_name_alive`, `uniq_category_slug_alive`) con `condition=Q(deleted_at__isnull=True)`.
- `class Meta(BaseModel.Meta)`: mantiene `db_table = 'categories'`, `ordering = ['name']`,
  `verbose_name_plural = 'categories'`.
- `save()` (autogeneración de slug) no cambia.

### Coexistencia `is_active` vs `deleted_at`

Ejes distintos, coexisten:

- `Category.is_active` = **visibilidad pública**. Staff oculta una categoría viva a los compradores.
- `deleted_at` = **borrado lógico**. La categoría sale de la app; recuperable por admin.

## Endpoints

No hay endpoints nuevos. Cambia el comportamiento de dos `DELETE` existentes.

### `DELETE /api/v1/categories/{id}/` (contrato modificado)

- **Permisos:** `IsAdminOrReadOnly` (sin cambios).
- **Comportamiento nuevo:** soft delete. `instance.delete()` setea `deleted_at`. La fila persiste
  en la base con `deleted_at` no nulo.
- **Respuestas:** `204` · `403` · `404`.
- **Efecto observable:** tras el `DELETE`, la categoría no aparece en `GET /api/v1/categories/` ni
  en su detalle (`404`), para staff y para anónimos. `Category.all_objects` la sigue viendo.
- `CategoryViewSet.get_queryset()` no necesita cambios de código: su base `Category.objects.all()`
  ahora ya excluye borrados. (Confirmar en la tarea que sigue devolviendo lo esperado.)

### `DELETE /api/v1/roles/{id}/` (contrato modificado)

- **Permisos:** `IsAdminOrReadOnly` (sin cambios).
- **Comportamiento nuevo:** soft delete. Como `instance.delete()` ya no borra físicamente, el FK
  `User.role` (`on_delete=PROTECT`) **no** dispara `ProtectedError`. Se reemplaza el `try/except
  ProtectedError` de `destroy()` por un guard explícito:
  - `if instance.users.exists()` → `409 Conflict` con `{"detail": "No se puede eliminar un rol con
    usuarios asignados."}` (mismo mensaje que hoy). La fila no se toca.
  - si no tiene usuarios → soft delete y `204`.
- El FK sigue siendo `on_delete=PROTECT` (protege contra `hard_delete` accidentales).
- **Respuestas:** `204` sin usuarios · `409` con usuarios · `403` · `404`.

> Ceiling conocido: la acción "delete selected" del admin de Django sobre un `Role` con usuarios
> asignados sigue cortando con `ProtectedError` (el collector corre antes que el override). El
> borrado individual desde el detalle del admin funciona. No se aborda en esta spec.

## Serializers

DRF **no** deriva `UniqueValidator` de un `UniqueConstraint` con `condition`. Al quitar
`unique=True` del campo hay que reponer la validación explícitamente, apuntada a las filas vivas:

- `apps/roles/serializers.py` → `RoleSerializer`: `code` con
  `validators=[UniqueValidator(queryset=Role.objects.all())]` (`Role.objects` = vivos).
- `apps/catalog/serializers.py` → `CategorySerializer`: `name` y `slug` con
  `UniqueValidator(queryset=Category.objects.all())`. El chequeo de colisión de slug autogenerado
  en `validate()` ya filtra sobre `Category.objects` → queda correcto sin cambios de lógica.

## Migraciones

- `apps/roles/migrations/0003_role_soft_delete.py`:
  - `AddField` `deleted_at` (nullable, `db_index=True`, default `NULL` → sin reescritura de filas).
  - `AlterField` `code` a `SlugField(max_length=32)` sin `unique`.
  - `RemoveConstraint`/índice único viejo de `code` + `AddConstraint` `uniq_role_code_alive`.
  - Reversible.
- `apps/catalog/migrations/0002_category_soft_delete.py`:
  - `AddField` `deleted_at`.
  - `AlterField` `name` y `slug` sin `unique`.
  - Swap de los índices únicos de `name` y `slug` por los `UniqueConstraint` parciales.
  - Reversible.
- `core` no tiene `migrations/` (BaseModel es abstracto): el campo aterriza en las migraciones de
  `roles` y `catalog`.
- La base actual (Neon) ya tiene `unique=True` sobre esas columnas, así que no puede haber
  duplicados que hagan fallar el `UniqueConstraint` parcial al aplicarse.

## Tareas

Ordenadas por dependencia. Cada una acotada a un archivo o una app.

1. `apps/core/models.py`: agregar `deleted_at` a `BaseModel`; `SoftDeleteQuerySet` (`alive`,
   `dead`, `delete` override, `hard_delete`); `SoftDeleteManager`; en `BaseModel` los métodos
   `delete()`, `hard_delete()`, `restore()`, los managers `objects` / `all_objects` y
   `Meta.base_manager_name = 'all_objects'`.
2. `apps/core/tests/`: `__init__.py` + `test_soft_delete.py`. Se ejercita el mixin a través de
   `Category` (el heredero concreto más liviano, sin FKs entrantes): `delete()` no borra la fila y
   setea `deleted_at`; `objects` la esconde y `all_objects` la ve; `restore()` la revive; el
   `delete()` bulk del queryset marca en masa sin borrar; `hard_delete()` (instancia y queryset)
   elimina de verdad; `alive()` / `dead()` parten el conjunto.
3. `apps/roles/models.py`: `RoleQuerySet(SoftDeleteQuerySet)`; managers `objects` (filtrado +
   `with_user_count`) y `all_objects`; `Meta(BaseModel.Meta)` con `constraints` = `UniqueConstraint`
   parcial sobre `code` y sin `unique=True` en el campo; `get_default_role()` sobre `all_objects`
   con restore si la fila está muerta.
4. `python manage.py makemigrations roles` → revisar `0003_role_soft_delete.py` (AddField +
   AlterField + swap de constraint). Confirmar que es reversible.
5. `apps/roles/serializers.py`: `UniqueValidator(queryset=Role.objects.all())` en `code`.
6. `apps/roles/views.py`: en `destroy()`, reemplazar el `try/except ProtectedError` por el guard
   `if instance.users.exists(): return Response(..., 409)`; si pasa, `super().destroy(...)`.
7. `apps/roles/admin.py`: `get_queryset()` → `Role.all_objects.with_user_count()`; agregar
   `deleted_at` a `list_display` y `list_filter`; acción `restore` que hace
   `queryset.update(deleted_at=None)`.
8. `apps/catalog/models.py`: `CategoryQuerySet(SoftDeleteQuerySet)`; managers `objects` (filtrado +
   `.active()`) y `all_objects`; `Meta(BaseModel.Meta)` con los dos `UniqueConstraint` parciales y
   sin `unique=True` en `name`/`slug`.
9. `python manage.py makemigrations catalog` → revisar `0002_category_soft_delete.py`. Confirmar
   reversibilidad.
10. `apps/catalog/serializers.py`: `UniqueValidator(queryset=Category.objects.all())` en `name` y
    `slug`.
11. `apps/catalog/views.py`: confirmar (y ajustar solo si hace falta) que `get_queryset()` sigue
    correcto ahora que `Category.objects` excluye borrados; sin cambio de lógica esperado.
12. `apps/catalog/admin.py`: `get_queryset()` → `Category.all_objects`; `deleted_at` en
    `list_display` y `list_filter`; acción `restore`. `prepopulated_fields` se mantiene.
13. Actualizar `apps/roles/tests/`:
    - `test_models.py`: `test_code_is_unique` sigue esperando `IntegrityError` al crear un `code`
      duplicado **entre filas vivas**; agregar un test que soft-deletea un `Role` y luego crea otro
      con el mismo `code` sin error (decisión 2). `get_default_role` idempotente aún tras soft
      delete del `customer`.
    - `test_api.py`: `test_delete_role_with_users_returns_409` sigue verde con el guard nuevo;
      agregar assertion de que `Role.all_objects.get(pk=...)` tiene `deleted_at` no nulo tras un
      `DELETE` sin usuarios; agregar `POST` que recrea un `code` recién soft-deleteado → `201`.
14. Actualizar `apps/catalog/tests/`:
    - `test_api.py`: `test_delete_by_staff` → tras `204`, `Category.objects.filter(pk=...)` es
      `False` **y** `Category.all_objects.get(pk=...)` existe con `deleted_at`; el detalle de esa
      categoría da `404`. Agregar `POST` que recrea un `name`/`slug` recién borrado → `201`.
    - `test_models.py`: agregar que `.active()` compone con `alive()` (una categoría activa pero
      soft-deleted no aparece en `Category.objects.active()`).

## Criterios de aceptación

- [ ] `python manage.py check` pasa sin errores.
- [ ] `python manage.py makemigrations --check --dry-run` no reporta migraciones faltantes.
- [ ] `python manage.py migrate` aplica limpio sobre una base vacía y sobre la base actual.
- [ ] `python manage.py migrate roles 0002 && python manage.py migrate catalog 0001` revierte sin
      error, y volver a `migrate` reaplica limpio.
- [ ] En un shell: `c = Category.objects.create(name='X'); c.delete()` deja
      `Category.all_objects.get(pk=c.pk).deleted_at` no nulo y `Category.objects.filter(pk=c.pk)`
      vacío. `c.restore()` lo revierte.
- [ ] `Category.objects.filter(...).delete()` marca `deleted_at` en todas y no elimina ninguna fila
      (`Category.all_objects.count()` no baja).
- [ ] `instance.hard_delete()` sí elimina la fila de la base.
- [ ] `DELETE /api/v1/categories/{id}/` (staff) → `204`; después la categoría no está en el listado
      ni en el detalle (`404`) para staff ni para anónimo, y `Category.all_objects` la ve.
- [ ] Tras soft-deletear "Beverages", `POST /api/v1/categories/` con `{"name": "Beverages"}` (staff)
      → `201` (decisión 2). Con la alternativa `unique=True`: este criterio se reemplaza por `400`.
- [ ] `DELETE /api/v1/roles/{id}/` de un rol sin usuarios (staff) → `204` y la fila queda con
      `deleted_at`.
- [ ] `DELETE /api/v1/roles/{id}/` del rol `customer` (con usuarios) → `409` con el `detail`
      esperado; el rol sigue vivo (`deleted_at` nulo).
- [ ] `POST /api/v1/roles/` con un `code` que pertenece a un rol vivo → `400`; con un `code` de un
      rol soft-deleteado → `201`.
- [ ] `get_default_role()` es idempotente aunque el rol `customer` haya sido soft-deleteado (no
      crea un duplicado; lo restaura).
- [ ] `user.role` sigue resolviendo aunque el `Role` apuntado esté soft-deleteado (no rompe con
      `DoesNotExist` — efecto de `base_manager_name = 'all_objects'`).
- [ ] En `/admin/`, las listas de `Role` y `Category` muestran filas borradas, la columna
      `deleted_at`, permiten filtrar por ella y tienen la acción `restore` que revive la selección.
- [ ] `python manage.py test apps.roles apps.catalog apps.core` pasa completo.
```
