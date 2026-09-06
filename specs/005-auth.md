# 005 — Autenticación JWT en `users`: registro, login y refresh

**Estado:** Aprobada
**Apps afectadas:** users (modificada), config (modificada)

## Objetivo

Dar de alta cuentas de usuario por API y autenticarlas con `djangorestframework-simplejwt`, para
que cualquier cliente (front, Swagger, tests) pueda registrarse, obtener un par de tokens
(access/refresh) y usar el access token contra los endpoints ya protegidos del resto de la API
(`roles`, `catalog`).

## Alcance

- `apps/users/serializers.py` (nuevo): `RegisterSerializer`.
- `apps/users/views.py` (nuevo): `RegisterView`.
- `apps/users/urls.py` (nuevo): rutas `auth/register/`, `auth/login/`, `auth/refresh/`, montadas
  bajo `/api/v1/` desde `config/urls.py`.
- Login y refresh se resuelven con las vistas estándar de `simplejwt`
  (`TokenObtainPairView`, `TokenRefreshView`), sin subclasificar: como `AUTH_USER_MODEL` ya define
  `USERNAME_FIELD = 'email'` (ver `apps/users/models.py`, spec `001-roles.md`), el serializer
  estándar de `simplejwt` ya pide `email` + `password` sin necesidad de código propio.
- `apps/users/tests/` (nuevo): tests de registro, login, refresh y el flujo end-to-end completo.

## Fuera de alcance

- Endpoint de perfil propio (`GET/PATCH /api/v1/auth/me/`). No lo pide el requerimiento; se agrega
  en otra spec si el front lo necesita.
- Logout / invalidación de refresh tokens (requiere la app `rest_framework_simplejwt.token_blacklist`,
  no instalada en `INSTALLED_APPS`). Fuera de alcance hasta que una spec lo justifique.
- Recuperación de contraseña, verificación de email, login social/OAuth.
- Claims extra en el payload del JWT (por ejemplo `role`). Si el front necesita el rol sin pedirlo
  aparte, se evalúa en otra spec.
- Throttling específico de los endpoints de auth. No hay `DEFAULT_THROTTLE_CLASSES` configurado hoy
  en `REST_FRAMEWORK`; no se agrega en esta spec.
- Cambiar `USERNAME_FIELD`, `REQUIRED_FIELDS` o cualquier otro campo de `apps/users/models.py`: no
  hay cambios de modelo en esta spec.

## Modelos

Sin cambios. Se reutiliza `User` tal como quedó definido en `001-roles.md`
(`apps/users/models.py`): `email` único y `USERNAME_FIELD`, `username` en `REQUIRED_FIELDS`, `role`
con default automático (`get_default_role`, `apps/roles/models.py`). No hay migración en esta spec.

## Endpoints

Rutas nuevas en `apps/users/urls.py`, incluidas desde `config/urls.py` bajo `/api/v1/`. Aparecen en
`/api/v1/docs/` por `drf-spectacular` (las vistas de `simplejwt` ya declaran `serializer_class`).

### `POST /api/v1/auth/register/`

- **Vista:** `RegisterView` (`generics.CreateAPIView`), `apps/users/views.py`.
- **Permisos:** `AllowAny`.
- **Serializer:** `RegisterSerializer`.
- **Request:**

```json
{
  "email": "ana@example.com",
  "username": "ana",
  "password": "una-clave-segura-123",
  "password2": "una-clave-segura-123",
  "first_name": "Ana",
  "last_name": "Gómez"
}
```

  `first_name` / `last_name` opcionales (heredan `blank=True` de `AbstractUser`). `role` **no** se
  acepta en el body: lo asigna el `default` del modelo (`customer`).

- **Validación:**
  - `email` único (`UniqueValidator` automático del `ModelSerializer` sobre el campo `unique=True`).
  - `username` único (ídem, campo `unique=True` heredado de `AbstractUser`).
  - `password` validado con `django.contrib.auth.password_validation.validate_password` (corre los
    `AUTH_PASSWORD_VALIDATORS` ya configurados en `config/settings/base.py`).
  - `password` y `password2` deben coincidir; si no, `400` con el error en `password2`.
- **Respuesta 201** (sin `password`, `role` de solo lectura expuesto como su `code`):

```json
{"id": 5, "email": "ana@example.com", "username": "ana", "first_name": "Ana",
 "last_name": "Gómez", "role": "customer"}
```

- **Respuestas:** `201` creado · `400` validación (contraseñas no coinciden, contraseña débil,
  email/username duplicado, campos requeridos faltantes).

### `POST /api/v1/auth/login/`

- **Vista:** `rest_framework_simplejwt.views.TokenObtainPairView`, usada directamente (sin
  subclase) en `apps/users/urls.py`.
- **Permisos:** `AllowAny` (default de la vista).
- **Request:** `{"email": "ana@example.com", "password": "una-clave-segura-123"}` — la clave del
  body es dinámica según `USERNAME_FIELD`; con `User.USERNAME_FIELD = 'email'` es `email`, no
  `username`.
- **Respuesta 200:** `{"access": "<jwt>", "refresh": "<jwt>"}`.
- **Respuestas:** `200` · `401` credenciales inválidas o cuenta inexistente.

### `POST /api/v1/auth/refresh/`

- **Vista:** `rest_framework_simplejwt.views.TokenRefreshView`, usada directamente en
  `apps/users/urls.py`.
- **Permisos:** `AllowAny` (default de la vista).
- **Request:** `{"refresh": "<jwt>"}`.
- **Respuesta 200:** `{"access": "<jwt-nuevo>"}`.
- **Respuestas:** `200` · `401` refresh token inválido, mal formado o expirado (`REFRESH_TOKEN_LIFETIME`
  = 7 días, `SIMPLE_JWT` en `config/settings/base.py`).

### Endpoint protegido para el flujo end-to-end

No se crea un endpoint nuevo: el criterio de aceptación end-to-end reutiliza
`GET /api/v1/roles/` (`IsAuthenticated`, spec `001-roles.md`) para probar que el access token emitido
por `/api/v1/auth/login/` (y el renovado por `/api/v1/auth/refresh/`) autentica correctamente contra
un endpoint ya protegido de la API.

## Serializers — `apps/users/serializers.py`

### `RegisterSerializer` (nuevo)

- `ModelSerializer` sobre `User`.
- `password = CharField(write_only=True, required=True, validators=[validate_password], style={'input_type': 'password'})`.
- `password2 = CharField(write_only=True, required=True, style={'input_type': 'password'})`.
- `role = CharField(source='role.code', read_only=True)`.
- `fields = ['id', 'email', 'username', 'first_name', 'last_name', 'password', 'password2', 'role']`.
- `read_only_fields = ['id']` (además de `role`, ya `read_only` por su declaración explícita).
- `validate(self, data)`: si `data['password'] != data['password2']` → `ValidationError({'password2': '...'})`;
  si coinciden, remueve `password2` de `data` antes de devolverla (no es un campo del modelo).
- `create(self, validated_data)`: `password = validated_data.pop('password')`;
  `User.objects.create_user(password=password, **validated_data)` (el manager por defecto de
  `AbstractUser` hashea la contraseña). No setea `role`: lo resuelve el `default` del campo.

## Vistas — `apps/users/views.py`

### `RegisterView` (nuevo)

- `generics.CreateAPIView`.
- `queryset = User.objects.all()`.
- `serializer_class = RegisterSerializer`.
- `permission_classes = [AllowAny]`.

## URLs — `apps/users/urls.py` (nuevo)

- Sin router (no es un `ModelViewSet`): `urlpatterns` con `path()` explícitos.
- `path('auth/register/', RegisterView.as_view(), name='auth-register')`.
- `path('auth/login/', TokenObtainPairView.as_view(), name='auth-login')`.
- `path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh')`.
- Import de `TokenObtainPairView` / `TokenRefreshView` desde `rest_framework_simplejwt.views`.

## Tareas

Ordenadas por dependencia. Cada una acotada a un archivo.

1. `apps/users/serializers.py`: `RegisterSerializer` (campos, `validate()`, `create()`) como se
   describe arriba. Import de `validate_password` desde
   `django.contrib.auth.password_validation`.
2. `apps/users/views.py`: `RegisterView`.
3. `apps/users/urls.py`: las tres rutas de auth (`register`, `login`, `refresh`).
4. `config/urls.py`: agregar `path('api/v1/', include('apps.users.urls'))`.
5. `apps/users/tests/__init__.py` + `apps/users/tests/test_api.py`:
   - Registro: `201` con body válido (verificar `role == 'customer'`, que `password` no está en la
     respuesta, y que `user.check_password(...)` es `True` en la base); `400` por contraseñas que no
     coinciden; `400` por contraseña débil (ej. `"123"`); `400` por `email` duplicado; `400` por
     `username` duplicado.
   - Login: `200` con `access` + `refresh` con credenciales correctas; `401` con password incorrecta;
     `401` con email inexistente.
   - Refresh: `200` con nuevo `access` a partir de un `refresh` válido; `401` con un `refresh`
     inválido/mal formado.
   - Flujo end-to-end: registrar un usuario → login con esas credenciales → `GET /api/v1/roles/`
     con el `access` obtenido → `200`; `GET /api/v1/roles/` sin token → `401`; refrescar con el
     `refresh` obtenido en el login → `GET /api/v1/roles/` con el `access` nuevo → `200`.

## Criterios de aceptación

- [ ] `python manage.py check` pasa sin errores.
- [ ] `POST /api/v1/auth/register/` con body válido → `201`; la respuesta no incluye `password`;
      incluye `"role": "customer"`; el usuario queda persistido con la contraseña hasheada
      (`user.check_password('...')` es `True`, `user.password` no es texto plano).
- [ ] `POST /api/v1/auth/register/` con `password` y `password2` distintos → `400` con el error en
      el campo `password2`.
- [ ] `POST /api/v1/auth/register/` con una contraseña débil (ej. `"123"`, o igual al `email`) →
      `400`.
- [ ] `POST /api/v1/auth/register/` con un `email` ya registrado → `400`; con un `username` ya
      registrado → `400`.
- [ ] `POST /api/v1/auth/login/` con `email` + `password` correctos → `200` con `access` y
      `refresh` presentes en la respuesta.
- [ ] `POST /api/v1/auth/login/` con `password` incorrecta, o con un `email` que no existe → `401`.
- [ ] `POST /api/v1/auth/refresh/` con un `refresh` válido → `200` con un `access` nuevo, distinto
      del original.
- [ ] `POST /api/v1/auth/refresh/` con un `refresh` inválido o mal formado → `401`.
- [ ] `GET /api/v1/roles/` sin header `Authorization` → `401`.
- [ ] **Flujo end-to-end:** registrar un usuario nuevo → loguearse con esas credenciales →
      `GET /api/v1/roles/` con `Authorization: Bearer <access>` → `200` → `POST /api/v1/auth/refresh/`
      con el `refresh` obtenido → `GET /api/v1/roles/` con el `access` renovado → `200`.
- [ ] Los tres endpoints (`register`, `login`, `refresh`) aparecen en `/api/v1/docs/`.
- [ ] `python manage.py test apps.users` pasa completo.
