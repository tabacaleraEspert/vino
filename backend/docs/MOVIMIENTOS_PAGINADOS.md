# GET /api/v1/movimientos (paginado)

Listado paginado de movimientos (Gastos/Ingresos).

## Request

```
GET /api/v1/movimientos?period=2026-02&tipo=Gasto&page=1&limit=50&sort=timestamp_desc
```

### Query params

| Param         | Tipo   | Default       | Descripción                              |
|---------------|--------|---------------|------------------------------------------|
| period        | string | —             | YYYY-MM (principal)                      |
| from, to      | date   | —             | Rango de fechas (alternativo a period)   |
| tipo          | string | Gasto         | Gasto \| Ingreso                         |
| user_id       | string | —             | Filtrar por Id_usuario                   |
| categoria     | string | —             | Por nombre                               |
| subcategoria  | string | —             | Por nombre                               |
| comercio      | string | —             | Contains                                 |
| min_amount    | float  | —             | Monto mínimo                             |
| max_amount    | float  | —             | Monto máximo                             |
| q             | string | —             | Buscar en comercio+descripcion            |
| categoria_id  | string | —             | Por ID de categoría                      |
| page          | int    | 1             | Página                                   |
| limit         | int    | 50            | Por página (max 5000)                    |
| sort          | string | timestamp_desc| timestamp_desc\|fecha_desc\|monto_desc\|monto_asc |

## Response 200

```json
{
  "items": [
    {
      "id": "120",
      "fecha": "2026-02-16",
      "timestamp": "2026-02-16T10:20:00-03:00",
      "tipo": "Gasto",
      "moneda": "ARS",
      "monto": 17200.0,
      "comercio": "MCDONALD",
      "descripcion": "Combo",
      "categoria": "Alimento",
      "subcategoria": "Fast food",
      "medio_pago": "Tarjeta"
    }
  ],
  "page": 1,
  "limit": 50,
  "total": 47
}
```

## Errores

- 400: period inválido
- 500: error de Sheets
