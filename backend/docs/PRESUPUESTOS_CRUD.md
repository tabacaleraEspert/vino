# CRUD Presupuestos (Sheets)

## Cambios

- **Antes:** GET desde Sheets; POST/PATCH/DELETE en `data.json`.
- **Ahora:** Todo usa **Google Sheets**.

## Contrato

### POST /api/v1/presupuestos

**Request:**
```json
{
  "categoryId": "1",
  "subcategoryId": null,
  "mes_anio": "2025-12",
  "amount": 500000,
  "period": "monthly",
  "spent": 0
}
```

- `subcategoryId` vacío/null = **presupuesto para toda la categoría** (general).
- `mes_anio` opcional; si no viene, se usa el mes actual (YYYY-MM).

**Response:** Objeto con `id`, `categoryId`, `subcategoryId`, `mes_anio`, `amount`, `period`, `spent`.

### PATCH /api/v1/presupuestos/{id}

Campos opcionales: `categoryId`, `subcategoryId`, `mes_anio`, `amount`.

### DELETE /api/v1/presupuestos/{id}

---

## Configuración Sheets

La hoja **Presupuesto** debe tener la columna **Timestamp** para que el POST funcione. Ver `SHEETS_SETUP.md`.
