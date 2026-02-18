# Cambios Backend: CRUD Categorías y Subcategorías (Sheets)

**Para el agente frontend** — Resumen de cambios en la API para integrar correctamente.

---

## 1. Fuente de datos

- **Antes:** GET leía de Sheets; POST/PATCH/DELETE escribían en `data.json` (store local). Los datos estaban desincronizados.
- **Ahora:** Todo (GET, POST, PATCH, DELETE) usa **Google Sheets**. Una sola fuente de verdad.

---

## 2. Contrato de la API

### `GET /api/v1/categorias`

**Respuesta:** Array de objetos con `id`, `nombre`, `icon`, `color`.

```json
[
  {
    "id": "1",
    "nombre": "Alimento",
    "icon": "🍔",
    "color": "#ef4444"
  }
]
```

- `icon` y `color` vienen del backend. Si no existen en Sheets, se usan defaults: `"📁"` y `"#6b7280"`.
- El frontend debe mapear `nombre` → `name` para el tipo `Category`.

---

### `POST /api/v1/categorias`

**Request body:**

```json
{
  "name": "Nueva categoría",
  "icon": "🍕",
  "color": "#22c55e",
  "subcategories": [
    { "name": "Sub 1" },
    { "name": "Sub 2" }
  ]
}
```

- `icon` y `color` son opcionales (defaults: `"📁"`, `"#6b7280"`).
- `subcategories` es opcional. Si se envía, se crean subcategorías en Sheets.

**Respuesta:** Objeto con `id`, `name`, `nombre`, `icon`, `color`.

```json
{
  "id": "7",
  "nombre": "Nueva categoría",
  "name": "Nueva categoría",
  "icon": "🍕",
  "color": "#22c55e"
}
```

---

### `PATCH /api/v1/categorias/{id}`

**Request body (parcial):**

```json
{
  "name": "Nombre actualizado",
  "icon": "🎬",
  "color": "#3b82f6"
}
```

- Solo se envían los campos a actualizar.
- Todos son opcionales.

**Respuesta:** Objeto con `id`, `nombre`, `name`, `icon`, `color`.

---

### `DELETE /api/v1/categorias/{id}`

**Respuesta:**

```json
{
  "deleted": true,
  "id": "7"
}
```

---

### `POST /api/v1/categorias/{id}/subcategorias`

**Request body:**

```json
{
  "name": "Nueva subcategoría"
}
```

**Respuesta:**

```json
{
  "id": "42",
  "name": "Nueva subcategoría",
  "categoryId": "1"
}
```

---

## 3. Tipos TypeScript sugeridos

```typescript
// Respuesta de GET /categorias
interface CategoriaRaw {
  id: string;
  nombre: string;
  icon?: string;
  color?: string;
}

// Mapeo a Category del frontend
interface Category {
  id: string;
  name: string;
  icon: string;
  color: string;
  subcategories?: Subcategory[];
}
```

Al mapear `CategoriaRaw` → `Category`:
- `name` = `cat.nombre`
- `icon` = `cat.icon || "📁"`
- `color` = `cat.color || "#6b7280"`

---

## 4. Errores posibles

| Código | Detalle | Causa |
|--------|---------|-------|
| 400 | `"La hoja Categoria necesita columna 'Timestamp'..."` | Faltan columnas en Sheets (Icon, Color, Timestamp) |
| 404 | `"Categoría no encontrada"` | Id inexistente |
| 404 | `"Categoría no encontrada"` (en POST subcategorias) | La categoría padre no existe |

---

## 5. Cambios ya hechos en el frontend

- `CategoriaRaw` incluye `icon?` y `color?`.
- `mapCatalogToCategories` usa `cat.icon` y `cat.color` con fallback a defaults.
- `CreateCategoryModal` ya envía `icon` y `color`.
- `api.categories.create`, `update`, `addSubcategory` ya apuntan a los endpoints correctos.

**No debería hacer falta cambiar el frontend** si ya estaba usando esos endpoints. Solo asegurarse de que `mapCatalogToCategories` use `icon` y `color` del backend cuando existan.
