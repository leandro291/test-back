# 004 — App de dominio `catalog`: modelo `Product`

**Estado:** Implementada y aprobada por el reviewer (2026-09-05) — las 7 decisiones confirmadas, incluida la sub-decisión 1 (validación blanda de host `cloudinary.com`).
**Apps afectadas:** catalog (modificada), config (modificada — solo si el include no cubre ya `catalog`)

## Objetivo

Sumar `Product` al catálogo: los productos que el ecommerce vende, clasificados por `Category`,
con una imagen servida desde Cloudinary. Expone un CRUD REST completo (lectura pública, escritura
para staff), filtros, búsqueda y un apartado en el admin. Es la primera feature que hereda el soft
delete de `003` desde cero.

## Alcance

- Modelo `Product(BaseModel)` en `apps/catalog/models.py` con `ProductQuerySet(SoftDeleteQuerySet)`.
- Migración `apps/catalog/migrations/0003_product.py` (`CreateModel` + `CheckConstraint` de precio).
- `ProductReadSerializer` y `ProductWriteSerializer` en `apps/catalog/serializers.py`.
- `ProductFilter` en `apps/catalog/filters.py`.
- `ProductViewSet` en `/api/v1/products/` (`apps/catalog/views.py`, `apps/catalog/urls.py`).
- `ProductAdmin` en `apps/catalog/admin.py`.
- Guard en `CategoryViewSet.destroy()`: `409` si la categoría tiene productos vivos asociados
  (modifica el contrato del `DELETE` de categorías descrito en `002` / `003`).
- Tests de modelo y de API en `apps/catalog/tests/`, más el ajuste del test de `DELETE` de
  categoría por el nuevo `409`.

## Fuera de alcance

- `ProductImage` / galería de varias imágenes por producto (el `SETUP.md` la reserva; va en otra
  spec).
- Subida de archivos a la API (sin `multipart`, sin `ImageField` / `CloudinaryField`). Las deps
  `cloudinary` / `django-cloudinary-storage` siguen sin uso hasta que exista `ProductImage`.
- `slug` de producto: el lookup de la URL es por `id`. Se agrega en otra spec si el front necesita
  URLs SEO.
- Descuento de `stock` al comprar, reservas de stock: es de la spec de `orders`.
- Precios promocionales / descuentos, variantes (talle, color), reseñas y rating.
- Cascada de soft delete de `Category` a sus `Product`: soft-deletear una categoría **no**
  soft-deletea sus productos. De hecho `on_delete=PROTECT` + el guard `409` impiden borrar una
  categoría mientras tenga productos vivos.
- Endpoint REST de `restore` (misma decisión que `003`: solo desde el admin).
- Cambiar el permiso de escritura a `role.code == 'admin'` (deuda heredada de `001` / `002`: hoy
  `is_staff`).

## Decisiones que el usuario DEBE confirmar antes de implementar

1. **`image_url` = `URLField(max_length=500, blank=True)`.** Guarda la URL de una imagen **ya
   subida** a Cloudinary (por el dashboard de Cloudinary o un widget de upload del front). La API
   **no** sube archivos. Campo opcional: un producto puede no tener imagen todavía.
   - Sub-decisión: ¿validar que el host de la URL sea de Cloudinary?
     - **Recomendación:** validación blanda y opcional — si viene no vacía, el host debe contener
       `cloudinary.com` (o `res.cloudinary.com`); si no, `400` con error de campo. Bloquea pegar
       una URL de cualquier lado por error, sin acoplarse a un `cloud_name` concreto.
     - Alternativa: aceptar cualquier URL http/https válida (solo la validación nativa de
       `URLField`). Menos código, menos garantías.
2. **Una sola imagen por producto** (`image_url` en `Product`). `ProductImage` queda fuera de
   alcance (ver arriba).
3. **FK a `Category` = `on_delete=PROTECT`** + `CategoryViewSet.destroy()` devuelve **409** si la
   categoría tiene productos **vivos** (`instance.products.exists()`, con `products` = manager por
   defecto = solo vivos). Una categoría cuyos únicos productos están soft-deleteados sí se puede
   borrar. Esto **modifica el contrato del `DELETE` de categorías** de `002` ("siempre procede") y
   de `003` (soft delete, siempre procede): ahora puede cortar con `409`. Se actualiza el test
   correspondiente de `catalog`.
4. **`Product` sin `slug`.** Lookup por `id`, consistente con `roles` y con el detalle de
   `categories`.
5. **`name` no único.** Un ecommerce real tiene productos con el mismo nombre (distinta marca,
   distinto vendedor). Sin `UniqueConstraint` de `name`.
6. **Visibilidad pública encadenada.** Para anónimos y no-staff, un producto se ve solo si:
   `is_active=True` **y** está vivo **y** su categoría está viva **y** `category.is_active=True`.
   Staff ve todos los productos vivos (incluidos los de categorías inactivas y los `is_active=False`).
   Los productos soft-deleteados solo se ven desde el admin.
7. **`price` con `CheckConstraint` a nivel base** además del validador de campo y del serializer
   (triple red, cada capa da un error distinto: DB, formulario Django, `400` de campo limpio).

## Modelos

### `Product` (nuevo) — `apps/catalog/models.py`

Hereda de `apps.core.models.BaseModel` → `created_at`, `updated_at`, `deleted_at`, soft delete,
`objects` / `all_objects`, `Meta.base_manager_name = 'all_objects'`.

| Campo | Tipo | Notas |
|---|---|---|
| `name` | `CharField(max_length=200)` | Requerido. **No único** (decisión 5). |
| `description` | `TextField(blank=True)` | Opcional. |
| `price` | `DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])` | Requerido. Ver `CheckConstraint` abajo. |
| `stock` | `PositiveIntegerField(default=0)` | Sin lógica de descuento acá (es de `orders`). |
| `is_active` | `BooleanField(default=True)` | Visibilidad pública, mismo eje que en `Category`. |
| `image_url` | `URLField(max_length=500, blank=True)` | URL de una imagen ya subida a Cloudinary (decisión 1). |
| `category` | `ForeignKey('catalog.Category', on_delete=models.PROTECT, related_name='products')` | Decisión 3. |

- `Meta(BaseModel.Meta)`:
  - `db_table = 'products'`
  - `ordering = ['name']` (override del `-created_at` del base; listados alfabéticos como `Category`)
  - `constraints = [CheckConstraint(condition=Q(price__gte=0), name='product_price_non_negative')]`
  - hereda `base_manager_name = 'all_objects'`
- Índices: el `ForeignKey` ya crea índice sobre `category_id`; `deleted_at` ya viene indexado del
  `BaseModel`. No se agregan más (YAGNI — se suman cuando un query lento lo justifique).
- `__str__` → `self.name`.
- **Sin `save()` custom** (no hay `slug` que generar).
- `ProductQuerySet(SoftDeleteQuerySet)`:
  - `active()` → `filter(is_active=True)`
  - `in_stock()` → `filter(stock__gt=0)`
  - `with_category()` → `select_related('category')`
  - `visible()` → `active().filter(category__is_active=True, category__deleted_at__isnull=True)`
    (producto activo + categoría viva y activa; compone sobre el `alive()` del manager por defecto)
- Managers:
  - `objects = SoftDeleteManager.from_queryset(ProductQuerySet)()` — solo vivos. Declarado primero.
  - `all_objects = ProductQuerySet.as_manager()` — todo, incluidos los borrados.
- Migración: `apps/catalog/migrations/0003_product.py` — `CreateModel` + `AddConstraint`. Sin data
  migration. Reversible.

## Endpoints

Router DRF en `apps/catalog/urls.py` (mismo `DefaultRouter` donde ya está `CategoryViewSet`),
incluido desde `config/urls.py` bajo `/api/v1/` (el include de `apps.catalog.urls` ya existe).
Aparece en `/api/v1/docs/` por `drf-spectacular`.

### `GET /api/v1/products/`

- **Permisos:** `IsAdminOrReadOnly` (lectura pública, incluido anónimo).
- **QuerySet:** base `Product.objects.with_category()`. Si `not (user and user.is_staff)` →
  `.visible()`. Staff → todos los vivos.
- **Filtros** (vía `ProductFilter`): `category` (id exacto), `price_min`, `price_max`, `is_active`
  (exacto, efectivo para staff), `in_stock` (`true` → `stock__gt=0`).
- **Búsqueda:** `search` sobre `name`, `description`.
- **Orden:** `name`, `price`, `created_at` (default `name`).
- **Respuesta 200:**

```json
{"count": 1, "results": [
  {"id": 1, "name": "Yerba Mate 1kg", "description": "", "price": "3499.00",
   "stock": 42, "is_active": true,
   "image_url": "https://res.cloudinary.com/demo/image/upload/v1/yerba.jpg",
   "category": {"id": 3, "name": "Beverages", "slug": "beverages"},
   "created_at": "...", "updated_at": "..."}
]}
```

### `GET /api/v1/products/{id}/`

- **Permisos:** `IsAdminOrReadOnly`.
- **Respuestas:** `200` · `404` (inexistente, soft-deleteado, o no visible para anónimo/no-staff —
  inactivo o con categoría inactiva/borrada).

### `POST /api/v1/products/`

- **Permisos:** requiere `is_staff`.
- **Serializer:** `ProductWriteSerializer`.
- **Request:** `{"name": "...", "description": "...", "price": "3499.00", "stock": 42,
  "is_active": true, "image_url": "https://res.cloudinary.com/...", "category": 3}`
  — `description` (default `""`), `stock` (default `0`), `is_active` (default `true`),
  `image_url` (default `""`) opcionales.
- **Validación:** `name` requerido; `price` requerido y `>= 0`; `category` requerido y debe ser una
  categoría **viva** (`Category.objects` = solo vivas → una categoría borrada da `400`); una
  categoría **inactiva** sí se acepta (el staff arma productos antes de publicar la categoría);
  `image_url` según decisión 1.
- **Respuestas:** `201` · `400` validación · `401` sin token · `403` autenticado sin staff.

### `PUT / PATCH /api/v1/products/{id}/`

- **Permisos:** requiere `is_staff`.
- **Serializer:** `ProductWriteSerializer`.
- **Request:** cualquier subconjunto de los campos escribibles.
- **Respuestas:** `200` · `400` · `403` · `404`.

### `DELETE /api/v1/products/{id}/`

- **Permisos:** requiere `is_staff`.
- **Comportamiento:** soft delete heredado de `BaseModel` (`instance.delete()` setea `deleted_at`;
  la fila persiste). No hay guard: un producto no tiene FKs entrantes todavía.
- **Respuestas:** `204` · `403` · `404`. Tras el `204`, el producto no aparece en el listado ni en
  el detalle (`404`) para nadie; `Product.all_objects` lo sigue viendo.

### `DELETE /api/v1/categories/{id}/` (contrato modificado — decisión 3)

- **Permisos:** `IsAdminOrReadOnly` (sin cambios).
- **Comportamiento nuevo:** `CategoryViewSet.destroy()` chequea
  `if instance.products.exists()` (manager por defecto → solo productos vivos) →
  `409 Conflict` con `{"detail": "No se puede eliminar una categoría con productos asociados."}`.
  La categoría no se toca. Si no tiene productos vivos → soft delete y `204` (como en `003`).
- **Respuestas:** `204` sin productos vivos · `409` con productos vivos · `403` · `404`.
- El `on_delete=PROTECT` del FK cubre además el `hard_delete` accidental (admin, shell).

> Ceiling conocido (igual que en `003` para `Role`): la acción "delete selected" del admin de
> Django sobre una categoría con productos vivos corta con `ProtectedError` antes del override.
> El borrado individual desde el detalle del admin y desde la API funcionan. No se aborda acá.

## Serializers — `apps/catalog/serializers.py`

### `CategorySlimSerializer` (nuevo)

- `ModelSerializer` sobre `Category`, solo lectura.
- `fields = ['id', 'name', 'slug']`.
- Representación anidada de `category` dentro de `ProductReadSerializer` (evita exponer todo el
  objeto categoría y evita otra consulta gracias al `select_related`).

### `ProductReadSerializer` (nuevo)

- `ModelSerializer` sobre `Product`.
- `category = CategorySlimSerializer(read_only=True)`.
- `fields = ['id', 'name', 'description', 'price', 'stock', 'is_active', 'image_url', 'category',
  'created_at', 'updated_at']`.
- `read_only_fields = ['id', 'created_at', 'updated_at']`.

### `ProductWriteSerializer` (nuevo)

- `ModelSerializer` sobre `Product`.
- `category = PrimaryKeyRelatedField(queryset=Category.objects.all())` — `Category.objects` = solo
  vivas → no se puede asociar un producto a una categoría borrada (da `400`).
- `fields = ['id', 'name', 'description', 'price', 'stock', 'is_active', 'image_url', 'category']`.
- `read_only_fields = ['id']`.
- `validate_price`: `>= 0` → si no, `serializers.ValidationError` (redundante con modelo y
  constraint, pero da error de campo limpio).
- `validate_image_url` (si se confirma la sub-decisión 1): si no vacío y el host no contiene
  `cloudinary.com` → `ValidationError`.

### `ProductViewSet.get_serializer_class()`

- `create` / `update` / `partial_update` → `ProductWriteSerializer`.
- resto (`list`, `retrieve`) → `ProductReadSerializer`.

## Filtros — `apps/catalog/filters.py`

### `ProductFilter` (nuevo)

- `FilterSet` sobre `Product`.
- `category`: `NumberFilter(field_name='category_id')` (id exacto).
- `price_min`: `NumberFilter(field_name='price', lookup_expr='gte')`.
- `price_max`: `NumberFilter(field_name='price', lookup_expr='lte')`.
- `is_active`: filtro exacto (efectivo para staff; para anónimo el queryset ya está acotado por
  `.visible()`).
- `in_stock`: `BooleanFilter(method='filter_in_stock')` → cuando `True`, `filter(stock__gt=0)`.
- `Meta.fields = ['category', 'is_active']` (los demás se declaran como atributos de clase).

Búsqueda y orden se configuran en el ViewSet, no en el `FilterSet` (mismo patrón que
`CategoryViewSet`): `search_fields = ['name', 'description']`,
`ordering_fields = ['name', 'price', 'created_at']`, `ordering = ['name']`.

## Vistas — `apps/catalog/views.py`

### `ProductViewSet` (nuevo)

- `ModelViewSet`.
- `permission_classes = [IsAdminOrReadOnly]`.
- `filterset_class = ProductFilter`.
- `search_fields = ['name', 'description']`.
- `ordering_fields = ['name', 'price', 'created_at']`, `ordering = ['name']`.
- `get_serializer_class()` como arriba.
- `get_queryset()`:
  - base: `Product.objects.with_category()`
  - si `not (self.request.user and self.request.user.is_staff)` → `.visible()`

### `CategoryViewSet` (modificado)

- Agregar `destroy()` con el guard `409` de la decisión 3 (patrón idéntico al de
  `RoleViewSet.destroy()`): si `instance.products.exists()` → `Response({'detail': ...}, 409)`;
  si no → `super().destroy(...)`.

## Admin — `apps/catalog/admin.py`

### `ProductAdmin` (nuevo)

- `@admin.register(Product)`.
- `list_display = ('name', 'category', 'price', 'stock', 'is_active', 'deleted_at')`.
- `list_filter = ('is_active', 'category', 'deleted_at')`.
- `search_fields = ('name',)`.
- `list_select_related = ('category',)`.
- `autocomplete_fields = ('category',)` (el `CategoryAdmin` ya tiene `search_fields = ('name',)`).
- `get_queryset()` → `Product.all_objects.select_related('category')` (el admin ve los borrados,
  patrón de `003`).
- `actions = ('restore',)` con `@admin.action(description='Restore selected products')` →
  `queryset.update(deleted_at=None)` (igual que `CategoryAdmin` / `RoleAdmin`).

## Tareas

Ordenadas por dependencia. Cada una acotada a un archivo.

1. `apps/catalog/models.py`: `ProductQuerySet(SoftDeleteQuerySet)` (`active`, `in_stock`,
   `with_category`, `visible`); `Product(BaseModel)` con los campos, `Meta` (`db_table`,
   `ordering`, `CheckConstraint`), `__str__`, managers `objects` / `all_objects`. Import de
   `Decimal` y `MinValueValidator`.
2. `python manage.py makemigrations catalog` → revisar `0003_product.py` (`CreateModel` +
   `AddConstraint`). Confirmar reversibilidad.
3. `apps/catalog/serializers.py`: `CategorySlimSerializer`, `ProductReadSerializer`,
   `ProductWriteSerializer` (con `validate_price` y, si se confirma, `validate_image_url`).
4. `apps/catalog/filters.py`: `ProductFilter`.
5. `apps/catalog/views.py`: `ProductViewSet` con `get_queryset()` y `get_serializer_class()`;
   agregar `destroy()` con el guard `409` a `CategoryViewSet` (import de `status`, `Response`).
6. `apps/catalog/urls.py`: registrar `ProductViewSet` en el router existente como `products`
   (`basename='product'`). Verificar que `config/urls.py` ya incluye `apps.catalog.urls` (sí).
7. `apps/catalog/admin.py`: `ProductAdmin`.
8. `apps/catalog/tests/test_models.py`: agregar `ProductModelTests` — `__str__`; defaults
   (`stock=0`, `is_active=True`, `image_url=''`); `price` negativo levanta `IntegrityError`
   (constraint); `full_clean()` con `price` negativo levanta `ValidationError`; `.in_stock()`
   parte por stock; `.visible()` excluye producto inactivo, producto de categoría inactiva y
   producto de categoría soft-deleteada; soft delete heredado (`delete()` no borra la fila,
   `objects` lo esconde, `all_objects` lo ve); `Category.delete()` físico / `hard_delete` con
   producto vivo levanta `ProtectedError`.
9. `apps/catalog/tests/test_api.py`: agregar `ProductAPITests` — matriz de permisos
   (`GET` anónimo `200`; `POST` sin token `401`, no-staff `403`, staff `201`; `PATCH`/`DELETE`
   igual); anónimo ve solo productos visibles (activo + categoría activa y viva); `404` al pedir
   el detalle de un producto no visible; filtros `category`, `price_min`, `price_max`, `in_stock`;
   `search`; orden por `price`; `POST` con `price` negativo `400`; `POST` con `category` de una
   categoría soft-deleteada `400`; `POST` con `image_url` no-Cloudinary `400` (si se confirma la
   sub-decisión); `DELETE` de producto → `204` + `Product.all_objects` lo ve con `deleted_at`,
   detalle `404`.
10. `apps/catalog/tests/test_api.py`: en `CategoryAPITests`, agregar
    `test_delete_category_with_products_returns_409` (categoría con un producto vivo → `409`, sigue
    viva) y `test_delete_category_with_only_soft_deleted_products_ok` (sus productos borrados → el
    `DELETE` procede con `204`). Revisar que `test_delete_by_staff` sigue verde (la `Snacks` del
    `setUpTestData` no tiene productos).

## Criterios de aceptación

- [ ] `python manage.py check` pasa sin errores.
- [ ] `python manage.py makemigrations --check --dry-run` no reporta migraciones faltantes.
- [ ] `python manage.py migrate` aplica limpio sobre una base vacía y sobre la base actual.
- [ ] `python manage.py migrate catalog 0002` revierte `0003_product` sin error; volver a `migrate`
      lo reaplica.
- [ ] `GET /api/v1/products/` sin token → `200` y pagina (`count` + `results`).
- [ ] Un anónimo **no** ve en el listado: productos `is_active=False`, productos de una categoría
      `is_active=False`, productos de una categoría soft-deleteada, ni productos soft-deleteados.
      Pedir el detalle de cualquiera de ellos → `404`.
- [ ] Un staff autenticado ve esos productos (los vivos) y `?is_active=false` los filtra.
- [ ] `?category=<id>` devuelve solo productos de esa categoría.
- [ ] `?price_min=1000&price_max=5000` acota por rango de precio (inclusive).
- [ ] `?in_stock=true` devuelve solo productos con `stock > 0`.
- [ ] `?search=<palabra>` filtra por `name` / `description`; `?ordering=price` ordena ascendente.
- [ ] La respuesta del listado trae `category` anidada (`{id, name, slug}`) y no dispara N+1
      (`select_related('category')` presente en `get_queryset()` vía `.with_category()`).
- [ ] `POST /api/v1/products/` sin token → `401`; con token no-staff → `403`; con token staff y
      body válido → `201`.
- [ ] `POST` con `price` `"-1.00"` → `400` con error en el campo `price`.
- [ ] `POST` con `category` apuntando a una categoría soft-deleteada → `400`.
- [ ] `POST` con `category` de una categoría **inactiva pero viva** → `201`.
- [ ] (Si se confirma la sub-decisión 1) `POST` con `image_url` cuyo host no contiene
      `cloudinary.com` → `400`; con una URL de `res.cloudinary.com` → `201`.
- [ ] `PATCH /api/v1/products/{id}/` con token staff → `200` y persiste; con no-staff → `403`.
- [ ] `DELETE /api/v1/products/{id}/` (staff) → `204`; después no está en el listado ni en el
      detalle (`404`) para nadie, y `Product.all_objects.get(pk=...)` existe con `deleted_at`.
- [ ] `DELETE /api/v1/categories/{id}/` de una categoría con al menos un producto vivo → `409` con
      el `detail` esperado; la categoría sigue viva.
- [ ] `DELETE /api/v1/categories/{id}/` de una categoría cuyos productos están todos soft-deleteados
      → `204`.
- [ ] `Product.objects.create(name='x', price=-1, category=c)` levanta `IntegrityError`
      (`CheckConstraint`).
- [ ] `Category` con un producto vivo: `category.hard_delete()` levanta `ProtectedError`.
- [ ] `ProductViewSet` aparece en `/api/v1/docs/`.
- [ ] En `/admin/`, el listado de productos muestra `name`, `category`, `price`, `stock`,
      `is_active`, `deleted_at`, permite filtrar por `is_active` / `category` / `deleted_at`, el
      campo `category` es autocomplete y la acción `restore` revive la selección.
- [ ] `python manage.py test apps.catalog apps.roles apps.core` pasa completo.
