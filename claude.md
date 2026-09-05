# Backend Ecommerce — Guía del proyecto

Backend de un ecommerce personal. Este archivo es el punto de entrada: define el stack, dónde vive
cada fuente de verdad y cómo se trabaja. No duplica contenido de las fuentes que referencia.

## Stack

| Pieza | Uso |
|---|---|
| Django | Framework base, admin |
| Django REST Framework | APIs REST |
| Simple JWT | Autenticación por token |
| Cloudinary | Almacenamiento de imágenes de producto |
| django-filter | Filtros de query params |
| django-cors-headers | CORS para los frontends |
| PostgreSQL | Base de datos (desde el inicio) |

## Fuentes de verdad

| Fuente | Qué define | Cuándo consultarla |
|---|---|---|
| `SETUP.md` | Estructura de carpetas, dependencias, variables de entorno, pasos de instalación | Antes de crear cualquier archivo o agregar una dependencia |
| Skill `django-patterns` | Patrones de código Django/DRF (settings, models, QuerySets, serializers, ViewSets, services) | **Obligatoria** para Developer y Reviewer antes de escribir o revisar Python |
| `specs/NNN-*.md` | Qué se construyó y por qué, tarea por tarea | Al retomar o extender una funcionalidad |

Regla: si algo contradice a `SETUP.md` o a `django-patterns`, gana la fuente, no el criterio del
momento. Si la fuente está mal, se corrige la fuente.

## Metodología: SDD (Spec Driven Development)

```
Requerimiento
     ↓
[orquestador]  ¿SDD o build directo?
     ↓ (SDD)
[spec]  genera specs/NNN-*.md  →  ⏸ ESPERA APROBACIÓN DEL USUARIO
     ↓ (aprobada)
[developer]  ejecuta las tareas en orden
     ↓
[reviewer]  verifica contra los criterios de aceptación
     ↓ hallazgos → vuelve a [developer]  (máx. 3 iteraciones)
     ↓ APROBADO
commit
```

Agentes en `.claude/agents/`:

- **[orquestador](.claude/agents/orquestador.md)** — decide si el requerimiento va por SDD o build directo.
- **[spec](.claude/agents/spec.md)** — traduce el requerimiento a una spec con tareas y criterios de aceptación. Se detiene a esperar aprobación.
- **[developer](.claude/agents/developer.md)** — ejecuta las tareas de la spec aprobada.
- **[reviewer](.claude/agents/reviewer.md)** — verifica la ejecución y devuelve hallazgos al developer.

Los cuatro corren con `model: claude-sonnet-5`.

## Reglas del proyecto

**Commits.** Un commit por funcionalidad completa y funcional, con mensaje descriptivo. Nunca
commits de trabajo parcial o en progreso. El commit se hace después de que el reviewer devuelve
`APROBADO`, no antes.

**Aprobación de specs.** El agente `spec` no delega al `developer` por su cuenta. Espera aprobación
explícita del usuario.

**Alcance.** No se agregan dependencias, apps ni abstracciones que la spec no pida. Caching,
signals y middleware personalizado se adoptan cuando una spec los justifica — los patrones están en
`django-patterns` para cuando haga falta.

**Secretos.** Nunca en el repo. Todo por variables de entorno (ver `SETUP.md`). `.env` está en
`.gitignore`; `.env.example` documenta las claves sin valores reales.

## Convenciones

- Respuestas al usuario y contenido de las specs: **español**.
- Código, nombres de variables, funciones, modelos, ramas y docstrings: **inglés**.
- Mensajes de commit: español, imperativo (`agrega autenticación JWT`, no `agregando`).
- API versionada bajo `/api/v1/`.
