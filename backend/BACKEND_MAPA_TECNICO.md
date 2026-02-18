# Mapa Técnico del Backend — Vino

**Fecha:** 2026-02-17  
**Objetivo:** Inventario completo, verificación de endpoints, riesgos y backlog priorizado.

---

## 1. INVENTARIO DE ARCHIVOS RELEVANTES

### Configuración y punto de entrada
| Path | Rol |
|------|-----|
| `app/main.py` | FastAPI app, CORS, montaje de router v1 en `/api/v1` |
| `app/core/config.py` | Settings (pydantic-settings): `GOOGLE_SHEETS_CREDENTIALS_FILE`, `GOOGLE_SHEETS_CREDENTIALS_JSON`, `SHEETS_REGISTRY_JSON`, SQL_*, JWT, CORS |
| `app/core/logging.py` | `configure_logging()` básico |
| `app/core/security.py` | JWT, `require_user`, `require_master_key` |

### SheetConfig y Google Sheets
| Path | Rol |
|------|-----|
| **`app/sheets/registry.py`** | **SheetConfig** (BaseModel: spreadsheet_id, worksheet, id_column, header_row) + dict `SHEETS` con configs para movimientos, reglas, categorias, subcategorias, presupuestos. `SPREADSHEET_ID` hardcodeado. |
| `app/sheets/client.py` | `get_sheets_service()` — lee creds de `GOOGLE_SHEETS_CREDENTIALS_FILE` o `GOOGLE_SHEETS_CREDENTIALS_JSON`, construye Sheets API v4 |
| `app/sheets/service.py` | Lectura/escritura movimientos: `read_table`, `list_movimientos`, `get_movimiento_by_id`, `create_movimiento`, `patch_movimiento_by_id` |
| `app/sheets/catalog_service.py` | Catálogos desde Sheets: `list_categorias`, `list_subcategorias`, `list_reglas`, `list_presupuestos` |

### Storage alternativo (JSON)
| Path | Rol |
|------|-----|
| `app/storage/store.py` | JSON en `backend/data.json`. Keys: `categories`, `budgets`, `merchants`, `merchantRules`. Usado por POST/PATCH/DELETE de categorias, reglas, presupuestos, comercios. **No sincronizado con Sheets.** |

### Routers (prefix `/api/v1`)
| Path | Prefix | Endpoints |
|------|--------|-----------|
| `app/api/v1/router.py` | — | Agrega health, auth, admin, comercios, views, movimientos, categorias, subcategorias, reglas, presupuestos |
| `app/api/v1/health.py` | — | `GET /health` |
| `app/api/v1/auth.py` | `/auth` | Auth endpoints |
| `app/api/v1/admin.py` | `/admin` | `POST /impersonate` (master key) |
| `app/api/v1/comercios.py` | `/comercios` | CRUD (store) |
| `app/api/v1/views.py` | `/views` | `GET /dashboard` (mock) |
| `app/api/v1/movimientos.py` | `/movimientos` | GET list, GET /{id}, POST, PATCH /{id} — **100% Sheets** |
| `app/api/v1/categorias.py` | `/categorias` | GET (Sheets), POST/PATCH/DELETE (store) |
| `app/api/v1/subcategorias.py` | `/subcategorias` | GET (Sheets, filtro `categoria_id`) |
| `app/api/v1/reglas.py` | `/reglas` | GET (Sheets), POST/PATCH/DELETE (store) |
| `app/api/v1/presupuestos.py` | `/presupuestos` | GET (Sheets), POST/PATCH/DELETE (store) |

### Modelos (no usados en movimientos actualmente)
| Path | Rol |
|------|-----|
| `app/models/movimiento.py` | Pydantic snake_case (fecha, tipo, monto, etc.) — **no alineado con headers Sheets** |
| `app/models/movimientos.py` | Pydantic alternativo (id_usuario, tipo_movimiento, etc.) — **no usado en endpoints** |

### Credenciales Google Sheets
- **Env vars:** `GOOGLE_SHEETS_CREDENTIALS_FILE` o `GOOGLE_SHEETS_CREDENTIALS_JSON`
- **Actual:** `.env` → `GOOGLE_SHEETS_CREDENTIALS_FILE=creds/service-account.json`
- **Opcional:** `SHEETS_REGISTRY_JSON` para registry dinámico (no implementado aún)

---

## 2. DIAGRAMA DE FLUJO — POST y PATCH Movimientos

```
POST /api/v1/movimientos
─────────────────────────────────────────────────────────────────────────
  payload (keys = headers Sheets, sin Id)
       │
       ▼
  create_movimiento(payload)
       │
       ├─► _get_headers_and_values_raw("movimientos")  → headers, values
       ├─► ts = _now_timestamp_iso_local()
       ├─► row_out = [payload[h] for h in headers], Id="", Timestamp=ts
       ├─► append(range, body={values: [row_out]})
       ├─► time.sleep(0.2)
       ├─► _get_headers_and_values_raw() + _find_row_index_by_column_value("Timestamp", ts)
       │      (retry 0.3s si no encuentra)
       └─► return row_dict (con Id ya generado por Sheet)
─────────────────────────────────────────────────────────────────────────


PATCH /api/v1/movimientos/{id}
─────────────────────────────────────────────────────────────────────────
  patch (solo columnas a actualizar, sin Id)
       │
       ▼
  patch_movimiento_by_id(id, patch)
       │
       ├─► _get_headers_and_values_raw("movimientos")
       ├─► idx = _find_row_index_by_column_value(headers, values, "Id", id)
       │      → KeyError si no existe
       ├─► row_number = header_row + 1 + idx
       ├─► updates = [ {range: A1, values: [[val]]} for col in patch if col != "Id" ]
       ├─► batchUpdate(spreadsheetId, body={data: updates})
       └─► get_movimiento_by_id(id) → return updated
─────────────────────────────────────────────────────────────────────────
```

---

## 3. VERIFICACIÓN DE ENDPOINTS

### Contrato esperado vs implementado

| Endpoint | Contrato | Estado | Request/Response ejemplo |
|----------|----------|--------|---------------------------|
| `GET /movimientos` | from, to, tipo, categoria, subcategoria, comercio, moneda, user_id, limit, offset, sort | ✅ OK | `?from=2026-02-01&to=2026-02-28&tipo=gasto&limit=1` → 200, lista |
| `GET /movimientos/{id}` | — | ✅ OK | `GET /movimientos/118` → 200, objeto con Id, Fecha, Timestamp, etc. |
| `POST /movimientos` | sin Id, backend setea Timestamp | ✅ OK | `POST {"Fecha":"17/02/2026","Id_usuario":"1",...}` → 201, objeto con Id generado |
| `PATCH /movimientos/{id}` | update parcial, no Id | ✅ OK | `PATCH {"Descripcion":"..."}` → 200, objeto actualizado |
| `GET /categorias` | — | ✅ OK | Lista con `id`, `nombre` (snake_case en output) |
| `GET /subcategorias?categoria_id=` | — | ✅ OK | `?categoria_id=1` → lista filtrada |
| `GET /reglas?comercio=&categoria_id=&subcategoria_id=` | — | ✅ OK | Filtros opcionales |
| `GET /presupuestos?mes_anio=&categoria_id=&subcategoria_id=` | — | ✅ OK | Filtros opcionales |

### Ejemplos verificados (2026-02-17)

```bash
# Health
curl http://localhost:8000/api/v1/health
# → {"ok":true}

# GET movimientos
curl "http://localhost:8000/api/v1/movimientos?limit=2"
# → [{"Id":"118","Fecha":"17/02/2026 ",...}, ...]

# GET movimientos/{id}
curl http://localhost:8000/api/v1/movimientos/118
# → {"Id":"118","Fecha":"17/02/2026 ",...}

# POST movimientos
curl -X POST http://localhost:8000/api/v1/movimientos \
  -H "Content-Type: application/json" \
  -d '{"Fecha":"17/02/2026","Id_usuario":"1","Medio de Carga":"Manual","Tipo de Movimiento":"gasto","Moneda":"ARS","Monto":"100","Medios de pago":"Efectivo","Descripcion":"Test API","Nombre_Categoria":"Otros","Nombre_SubCategoria":"Gastos no categorizados","Comercio":"Test"}'
# → {"Id":"121","Fecha":"17/02/2026","Timestamp":"2026-02-17T19:10:22.827-03:00",...}

# PATCH movimientos
curl -X PATCH http://localhost:8000/api/v1/movimientos/121 \
  -H "Content-Type: application/json" \
  -d '{"Descripcion":"Test API - actualizado"}'
# → {"Id":"121",...,"Descripcion":"Test API - actualizado",...}

# 404
curl http://localhost:8000/api/v1/movimientos/99999
# → {"detail":"Movimiento no encontrado"}
```

### Observaciones

- **Movimientos:** Respuesta usa headers exactos de Sheets (Id, Fecha, Timestamp, Nombre_Categoria, etc.). No hay normalización a snake_case.
- **Catálogos:** `catalog_service` ya normaliza a snake_case en la salida (id, nombre, categoria_id, mes_anio, etc.).
- **Categorías, Reglas, Presupuestos:** GET lee de Sheets; POST/PATCH/DELETE escriben en `data.json`. **Datos desincronizados** — lo creado por API no aparece en GET.

---

## 4. RIESGOS Y MITIGACIONES

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| **Concurrencia Sheets** | Media | Dos POST simultáneos pueden generar Timestamps muy cercanos; el lookup por Timestamp podría fallar o confundir filas. Mitigación: agregar sufijo aleatorio al Timestamp o usar retry con backoff. |
| **Headers con espacios** | Baja | "Tipo de Movimiento", "Medio de Carga", "Medios de pago" — el mapeo es correcto si el payload usa exactamente esos nombres. Documentar contrato. |
| **Inconsistencia Sheets vs Store** | Alta | Categorías, Reglas, Presupuestos: GET=Sheets, POST/PATCH/DELETE=JSON. El frontend verá datos distintos según operación. Mitigación: unificar fuente (Sheets o store) o sincronizar. |
| **Id generado por Sheet** | Media | Si la hoja usa fórmula (ej. ROW()), el Id puede no estar disponible de inmediato. El sleep(0.2) y retry mitigan; considerar aumentar si falla en producción. |
| **Fórmulas en Sheets** | Baja | Columnas como "Check de Concat", "Chech ID-Categoria" pueden ser fórmulas. El PATCH no las sobrescribe si no están en patch; el append puede afectar columnas calculadas. |
| **Parseo de Fecha** | Media | Sheets usa "dd/mm/yyyy"; query params usan "yyyy-mm-dd". El service parsea correctamente. Fallo si formato cambia. |
| **Monto con coma** | Baja | "25,000" se parsea con `_parse_monto` (reemplaza coma). OK. |
| **Colisión de nombres** | Baja | Ya mitigado: handlers `get_*`, `post_*`, `patch_*`; servicios importados como `svc_list_movimientos`. |

---

## 5. BACKLOG PRIORIZADO

### P0 — Crítico
| # | Item | Esfuerzo | Impacto |
|---|------|----------|---------|
| 1 | **Unificar fuente de datos para Categorías, Reglas, Presupuestos** — Decidir: o todo Sheets (implementar write en Sheets) o todo store (cambiar GET a store). Hoy hay split que rompe consistencia. | Alto | Alto |
| 2 | **Logging de errores Sheets** — En `create_movimiento`, `patch_movimiento_by_id`, `read_table`: capturar excepciones de API, loguear con `logging.exception`, re-raise como HTTPException 503 con detail genérico. | Bajo | Alto |

### P1 — Importante
| # | Item | Esfuerzo | Impacto |
|---|------|----------|---------|
| 3 | **Normalización DTOs movimientos** — Definir `MovimientoOut` con snake_case (id, fecha, timestamp, id_usuario, tipo_movimiento, monto, etc.) y mapear desde dict raw de Sheets. Mantener contrato estable para frontend. | Medio | Alto |
| 4 | **PATCH reglas y presupuestos en Sheets** — Si se unifica a Sheets: implementar `patch_regla_by_id`, `patch_presupuesto_by_id` en service/catalog_service y exponer en routers. | Medio | Medio |
| 5 | **Cacheo opcional de catálogos** — TTL 5–10 min para categorias, subcategorias, reglas, presupuestos. Reducir llamadas a Sheets API. | Medio | Medio |
| 6 | **Registry desde env** — `SHEETS_REGISTRY_JSON` para cargar config dinámicamente; fallback al registry actual. | Bajo | Bajo |

### P2 — Mejora
| # | Item | Esfuerzo | Impacto |
|---|------|----------|---------|
| 7 | **Validación POST movimientos** — Pydantic model que acepte keys de Sheets y valide tipos (Fecha, Monto, etc.). | Bajo | Medio |
| 8 | **Paginación con total** — `GET /movimientos` devolver `{ items: [...], total: N }` para UI de paginación. | Bajo | Medio |
| 9 | **Robustez POST** — Timestamp con uuid4 suffix para evitar colisiones; retry con backoff en lookup. | Bajo | Medio |
| 10 | **Eliminar modelos duplicados** — `app/models/movimiento.py` vs `movimientos.py`; consolidar o eliminar si no se usan. | Bajo | Bajo |

---

## 6. PLAN DE MIGRACIÓN A SQL (PROPUESTA — NO IMPLEMENTADO)

### Objetivo
Mantener contrato REST idéntico; cambiar storage de Sheets a Azure SQL sin que el frontend note la diferencia.

### Patrón Repository/Service

```
Routers (app/api/v1/*)
    │
    ▼
Services (app/services/movimientos_service.py, catalog_service.py)
    │  — Lógica de negocio, validación, mapeo DTO
    ▼
Repositories (app/repositories/movimientos_repo.py, etc.)
    │  — Interfaz: list(), get_by_id(), create(), patch()
    ▼
Implementaciones:
    - SheetsMovimientosRepo (actual)
    - SqlMovimientosRepo (futuro)
```

### Estrategia de IDs
- **Hoy (Sheets):** Id generado por hoja (fórmula ROW() o similar); Timestamp como correlación en POST.
- **Mañana (SQL):** Id autoincremental; `timestamp` o `external_key` (UUID) para correlación. El DTO `MovimientoOut` expone `id` (int o string) — el frontend ya usa string.
- **Migración:** Script que lee Sheets, inserta en SQL, preserva Id original en columna `legacy_id` si se necesita para referencias durante transición.

### Pasos sugeridos
1. Extraer lógica de `app/sheets/service.py` a `MovimientosRepository` con interfaz abstracta.
2. Implementar `SheetsMovimientosRepository` que delega al código actual.
3. Crear `SqlMovimientosRepository` con SQLAlchemy/async, mapeo a tablas.
4. Inyectar repo vía dependency (FastAPI `Depends`) según config `STORAGE_BACKEND=sheets|sql`.
5. Repetir para categorias, subcategorias, reglas, presupuestos.
6. Tests de integración que validen mismo contrato con ambos backends.

---

## 7. MEJORAS LOW EFFORT / HIGH IMPACT

| Mejora | Esfuerzo | Impacto |
|--------|----------|---------|
| Normalización DTOs movimientos (snake_case en response) | Medio | Alto — Frontend puede tipar y mantener consistencia |
| Cacheo catálogos (TTL 5 min) | Medio | Alto — Menos latencia, menos cuota Sheets |
| PATCH reglas y presupuestos en Sheets | Medio | Medio — Completar CRUD real |
| Logging consistente en fallos Sheets | Bajo | Alto — Debug en producción |
| Unificar fuente categorías/reglas/presupuestos | Alto | Crítico — Eliminar confusión de datos |

---

*Documento generado por análisis del código y verificación manual de endpoints.*
