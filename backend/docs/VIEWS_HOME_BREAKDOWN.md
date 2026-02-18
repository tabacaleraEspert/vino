# GET /api/v1/views/home/breakdown

Gastos por categoría (top N), transacciones recientes, mayor_gasto, transacciones_count.

## Request

```
GET /api/v1/views/home/breakdown?period=2026-02&user_id=1&currency=ARS&top_categories=6&recent_limit=5&include_zeros=false
```

### Query params

| Param            | Tipo   | Obligatorio | Default | Descripción                          |
|------------------|--------|-------------|---------|--------------------------------------|
| period           | string | Sí          | —       | YYYY-MM                              |
| user_id          | string | No          | "1"     | Filtrar por Id_usuario               |
| currency         | string | No          | ARS     | Filtrar por Moneda                   |
| top_categories   | int    | No          | 6       | Cantidad en "Gastos por categoría"   |
| recent_limit     | int    | No          | 5       | Transacciones recientes              |
| include_zeros    | bool   | No          | false   | Incluir categorías con $0            |

## Response 200

```json
{
  "period": "2026-02",
  "user_id": "1",
  "currency": "ARS",
  "gastos_por_categoria": [
    {"categoria": "Otros", "total": 1005983.0, "pct": 0.61},
    {"categoria": "Transporte", "total": 572742.0, "pct": 0.35}
  ],
  "transacciones_recientes": [
    {
      "id": "120",
      "fecha": "2026-02-16",
      "timestamp": "2026-02-16T10:20:00-03:00",
      "titulo": "MCDONALD",
      "descripcion": "MCDONALD",
      "comercio": "MCDONALD",
      "categoria": "Alimento",
      "subcategoria": "Fast food",
      "monto": 17200.0
    }
  ],
  "mayor_gasto": 200000.0,
  "transacciones_count": 47
}
```

- **titulo**: Comercio si existe, si no Descripcion, si no "Sin descripción"
- **pct**: porcentaje del total de gastos del mes
