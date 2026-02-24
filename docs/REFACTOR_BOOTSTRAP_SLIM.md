# Plan de Refactorización: Bootstrap Slim → Endpoints Separados

## 1. Endpoints Backend Disponibles (sin modificar backend)

| Endpoint | Método | Params | Uso |
|----------|--------|--------|-----|
| `/categorias` | GET | - | Lista categorías |
| `/categorias` | POST | body | Crear categoría |
| `/categorias/{id}` | PATCH, DELETE | - | Actualizar/eliminar |
| `/categorias/{id}/subcategorias` | POST | body | Crear subcategoría |
| `/subcategorias` | GET | `categoria_id?` | Lista subcategorías |
| `/subcategorias/{id}` | PATCH, DELETE | - | Actualizar/eliminar |
| `/comercios` | GET | - | Lista comercios (store) |
| `/comercios` | POST, PATCH, DELETE | - | CRUD comercios |
| `/reglas` | GET | `comercio?`, `categoria_id?`, `subcategoria_id?` | Lista reglas |
| `/reglas` | POST, PATCH, DELETE | - | CRUD reglas |
| `/presupuestos` | GET | `mesAño?`, `categoria_id?`, `subcategoria_id?` | Lista presupuestos |
| `/presupuestos` | POST, PATCH, DELETE | - | CRUD presupuestos |
| `/movimientos` | GET | `period`, `from`, `to`, `page`, `limit`, `tipo`, `categoria_id`, `subcategoria_id`, `comercio`, `q`, etc. | Lista paginada |
| `/movimientos` | POST, PATCH, DELETE | - | CRUD movimientos |
| `/views/home/summary` | GET | `period`, `moneda?` | Resumen Dashboard |
| `/views/home/breakdown` | GET | `period`, `currency?`, `top_categories?`, `recent_limit?` | Breakdown Dashboard |
| `/bootstrap` | GET | - | **Legacy** - todo en uno |

---

## 2. Mapeo Pantalla → Endpoints a consumir

| Pantalla | Endpoints necesarios | Cuándo cargar |
|----------|----------------------|---------------|
| **Dashboard** | `/categorias`, `/subcategorias`, `/views/home/summary`, `/views/home/breakdown`, `/presupuestos?mesAño=` (fallback) | Inicial: catálogos + views. Presupuestos: lazy si summary trae presupuesto_mes |
| **Movimientos** | `/categorias`, `/subcategorias`, `/comercios`, `/movimientos` | Inicial: catálogos. Movimientos: al montar con period. Comercios: lazy o junto con movs |
| **Categorías** | `/categorias`, `/subcategorias` | Inicial (catálogos) |
| **Presupuestos** | `/categorias`, `/subcategorias`, `/presupuestos`, `/movimientos` (para spent) | Catálogos inicial. Presupuestos + movimientos al abrir |
| **Comercios** | `/comercios`, `/reglas`, `/movimientos` (para virtuales) | Lazy: al abrir pantalla |
| **MerchantDetail** | Idem Comercios + reglas por comercio | Lazy: al abrir detalle |
| **Reglas** | `/reglas`, `/categorias`, `/subcategorias` | Lazy: al abrir pantalla |
| **Stats** | `/categorias`, `transactions` (ya en context o fetch) | Catálogos inicial, transactions del mes |

---

## 3. Bootstrap SLIM (catálogos de baja variación)

**Contenido:** Solo `categorias` + `subcategorias`.

**Implementación:** No existe endpoint único. Usar:
- `GET /categorias`
- `GET /subcategorias`

**Cache:**
- Key: `catalog_${user.id}`
- TTL: 24h (86400s)
- Storage: localStorage con `{ data, lastFetchTs }`
- Invalidación: botón "Actualizar datos", o al hacer CRUD de categorías/subcategorías

**ETag:** El backend no expone ETag. Usar TTL + invalidación manual.

---

## 4. Movimientos (endpoint dedicado)

**Endpoint:** `GET /movimientos`

**Params soportados:**
- `period` (YYYY-MM)
- `from`, `to` (fechas)
- `page`, `limit` (1–5000)
- `tipo` (Gasto/Ingreso)
- `categoria_id`, `subcategoria_id`, `comercio`, `q`, `min_amount`, `max_amount`, `medio_carga`, `moneda`
- `sort`: `timestamp_desc`, `fecha_desc`, `monto_desc`, `monto_asc`

**Implementación:**
- Siempre paginado (ej. limit=50 por defecto)
- Infinite scroll o "Cargar más"
- Estado: loading, error, empty
- No incluir en bootstrap

---

## 5. Reglas y Comercios (lazy load)

**Reglas:** `GET /reglas` — cargar solo al abrir pantalla Reglas o Comercios/MerchantDetail.

**Comercios:** `GET /comercios` devuelve solo store. Los "virtuales" se construyen con:
- Nombres únicos de `reglas[].comercio`
- Nombres únicos de `movimientos[].comercio` (o `descripcion`)
- Excluir los que ya están en store

**Cache:** 10 min en memoria (no localStorage). Invalidar al crear/editar regla o comercio.

---

## 6. Presupuestos

**Endpoint:** `GET /presupuestos?mesAño=YYYY-MM`

**Uso:**
- Dashboard: `presupuesto_mes` viene en `/views/home/summary`. Si falta, fallback a suma de `GET /presupuestos`.
- Pantalla Presupuestos: cargar al abrir.
- Para `spent`: usar transacciones del mes (ya en context o fetch dedicado).

---

## 7. Deuda técnica (sin endpoint dedicado)

| Dato | Situación | Acción |
|------|-----------|--------|
| Comercios virtuales | No hay `GET /comercios/virtual` | Construir en frontend desde reglas + movimientos |
| Medios de pago | No hay endpoint | No implementar; ignorar si no existe |

---

## 8. Archivos a modificar

| Archivo | Cambios |
|---------|---------|
| `frontend/src/lib/api.ts` | Mantener; ya tiene todos los endpoints. Añadir helpers de cache si aplica |
| `frontend/src/lib/dataLayer.ts` | **NUEVO** – capa de datos: fetch, cache, coalescing |
| `frontend/src/app/context/DataContext.tsx` | Refactor: eliminar bootstrap, cargar por dominios (catalog, movements, budgets, merchants, rules) |
| `frontend/src/app/context/CatalogContext.tsx` | **NUEVO** (opcional) – categorías + subcategorías con cache |
| `frontend/src/app/components/Dashboard.tsx` | Usar catalog + views; no depender de budgets si summary trae presupuesto_mes |
| `frontend/src/app/components/Transactions.tsx` | Usar movimientos paginados; filtros; infinite scroll |
| `frontend/src/app/components/Budgets.tsx` | Lazy load presupuestos + movimientos |
| `frontend/src/app/components/Merchants.tsx` | Lazy load comercios + reglas + movimientos |
| `frontend/src/app/components/MerchantDetail.tsx` | Idem |
| `frontend/src/app/components/Categories.tsx` | Usar solo catalog (categorias+subcategorias) |
| `frontend/src/app/components/Stats.tsx` | Usar catalog + transactions |
| `frontend/src/app/App.tsx` | Providers: CatalogProvider, DataProvider (reducido) |
| `frontend/src/app/components/RootLayout.tsx` | Botón "Actualizar datos" para invalidar cache |

---

## 9. Estrategia de cache

| Recurso | Cache | TTL | Invalidación |
|---------|-------|-----|--------------|
| categorias + subcategorias | localStorage | 24h | CRUD categoría/subcategoría, botón "Actualizar" |
| presupuestos | memoria | 5 min | CRUD presupuesto, cambio mes |
| reglas | memoria | 10 min | CRUD regla |
| comercios (store) | memoria | 10 min | CRUD comercio |
| movimientos | no cache | - | Siempre fetch fresco (paginado) |
| views/home/* | memoria | 2 min | Cambio period |

---

## 10. Plan de rollout

1. **Fase 1 – Data layer**
   - Crear `dataLayer.ts` con fetch + coalescing
   - Implementar cache para catalog (localStorage)

2. **Fase 2 – CatalogContext**
   - Crear CatalogContext (categorias + subcategorias)
   - Migrar componentes que solo usan catalog

3. **Fase 3 – DataContext refactor**
   - Eliminar bootstrap
   - Cargar movimientos por endpoint
   - Lazy load: presupuestos, reglas, comercios

4. **Fase 4 – Pantallas**
   - Transactions: paginación + filtros
   - Merchants/MerchantDetail: lazy load
   - Budgets: lazy load

5. **Feature flag (opcional)**
   - `VITE_USE_SLIM_BOOTSTRAP=true` para A/B
   - Logging: `performance.now()` antes/después de fetch, `response.size` si disponible

---

## 11. Pseudo-código / Código concreto

### 11.1 dataLayer.ts (nuevo)

```typescript
// frontend/src/lib/dataLayer.ts

const CACHE_KEYS = {
  catalog: (userId: string) => `catalog_${userId}`,
};
const CATALOG_TTL_MS = 24 * 60 * 60 * 1000; // 24h

const inFlight = new Map<string, Promise<unknown>>();

function coalesce<T>(key: string, fn: () => Promise<T>): Promise<T> {
  if (inFlight.has(key)) return inFlight.get(key) as Promise<T>;
  const p = fn().finally(() => inFlight.delete(key));
  inFlight.set(key, p);
  return p;
}

export async function fetchCatalog(token: string, userId: string) {
  const cacheKey = CACHE_KEYS.catalog(userId);
  const cached = localStorage.getItem(cacheKey);
  if (cached) {
    const { data, lastFetchTs } = JSON.parse(cached);
    if (Date.now() - lastFetchTs < CATALOG_TTL_MS) return data;
  }
  return coalesce(`catalog_${userId}`, async () => {
    const [cats, subs] = await Promise.all([
      api.categories.list(token),
      api.subcategorias.list({}, token),
    ]);
    const data = { categorias: cats, subcategorias: subs };
    localStorage.setItem(cacheKey, JSON.stringify({ data, lastFetchTs: Date.now() }));
    return data;
  });
}

export function invalidateCatalog(userId: string) {
  localStorage.removeItem(CACHE_KEYS.catalog(userId));
}
```

### 11.2 DataContext refactor (fetchData)

```typescript
// Reemplazar fetchData actual por:

const fetchCatalog = async () => {
  const { categorias, subcategorias } = await fetchCatalogFromLayer(token, user.id);
  const cats = mapCatalogToCategories(categorias, subcategorias);
  setCategories(cats);
};

const fetchMovements = async () => {
  const period = `${selectedMonth.year}-${String(selectedMonth.month + 1).padStart(2, "0")}`;
  const res = await api.movimientos.list({ period, limit: "1000", page: 1 }, token);
  const items = res.items ?? [];
  const mapped = items.map(m => mapMovimientoItemToTransaction(m, categories, merchants));
  setTransactions(mapped);
};

// Carga inicial: solo catalog + movements
useEffect(() => {
  if (!token) return;
  (async () => {
    setIsLoading(true);
    await fetchCatalog();
    await fetchMovements(); // categories ya disponible para mapping
    setIsLoading(false);
  })();
}, [token, selectedMonth]);

// Lazy: presupuestos (cuando se abre Budgets o Dashboard necesita)
// Lazy: reglas, comercios (cuando se abre Merchants/Reglas)
```

### 11.3 Merchants – lazy load

```typescript
// En Merchants.tsx o en DataContext con flag "merchantsLoaded"

const loadMerchants = async () => {
  const [comercios, reglas, movs] = await Promise.all([
    api.merchants.list(token),
    api.merchantRules.list({}, token),
    api.movimientos.list({ period, limit: "500" }, token),
  ]);
  const namesFromReglas = [...new Set(reglas.map(r => r.comercio).filter(Boolean))];
  const namesFromMovs = [...new Set(movs.items.map(m => m.comercio || m.descripcion).filter(Boolean))];
  const allNames = [...new Set([...namesFromReglas, ...namesFromMovs])];
  const storeNames = new Set(comercios.map(c => c.name.toLowerCase()));
  const virtual = allNames.filter(n => !storeNames.has(n.toLowerCase()))
    .map(n => ({ id: `comercio-${n.replace(/\s+/g, "_")}`, name: n }));
  setMerchants([...comercios, ...virtual]);
  setMerchantRules(mapReglasToMerchantRules(reglas, merchants));
};
```

---

## 12. Resumen de endpoints por pantalla (post-refactor)

| Pantalla | Llamadas |
|----------|----------|
| **Dashboard** | GET /categorias, GET /subcategorias (cache), GET /views/home/summary, GET /views/home/breakdown |
| **Movimientos** | Catalog (cache), GET /movimientos?period=&page=&limit= |
| **Categorías** | Catalog (cache) |
| **Presupuestos** | Catalog (cache), GET /presupuestos?mesAño=, GET /movimientos (para spent) |
| **Comercios** | GET /comercios, GET /reglas, GET /movimientos (lazy) |
| **MerchantDetail** | Idem Comercios (lazy) |
| **Reglas** | GET /reglas, Catalog (lazy) |
| **Stats** | Catalog (cache), transactions (del context) |

---

## 13. Restricciones cumplidas

- ✅ Solo endpoints existentes
- ✅ No modificar backend
- ✅ Comercios virtuales: construidos en frontend (deuda documentada)
- ✅ Contrato de datos (tipos) preservado
- ✅ Deduplicación (coalescing) en data layer
- ✅ Cache + TTL + invalidación manual (sin ETag)
