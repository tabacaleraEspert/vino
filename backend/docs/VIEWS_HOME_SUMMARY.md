# GET /api/v1/views/home/summary

Endpoint para la tarjeta de Inicio: **Gastado del mes / Presupuesto / Usado%**.

## Request

```
GET /api/v1/views/home/summary?period=2025-10&moneda=ARS
```

### Query params

| Param    | Tipo   | Obligatorio | Default | Descripción                          |
|----------|--------|-------------|---------|--------------------------------------|
| period   | string | Sí          | —       | Formato `YYYY-MM` (ej: `2025-10`)    |
| moneda   | string | No          | `ARS`   | Filtrar movimientos por Moneda       |

**Nota:** `Id_usuario` está hardcodeado a `"1"` en el backend.

## Response

```json
{
  "period": "2025-10",
  "user_id": "1",
  "moneda": "ARS",
  "gasto_mes": 123456.78,
  "presupuesto_mes": 5320000.00
}
```

- **usado_pct** se calcula en el frontend: `gasto_mes / presupuesto_mes` (si `presupuesto_mes == 0` → `0`).

## Errores

| Código | Detalle                    | Causa                          |
|--------|----------------------------|--------------------------------|
| 400    | `period es obligatorio`    | Falta query param `period`     |
| 400    | `period debe ser YYYY-MM`  | Formato de `period` inválido  |
| 400    | `period inválido`          | Mes/año fuera de rango        |

## Ejemplos curl

```bash
# Básico (period obligatorio)
curl "http://127.0.0.1:8000/api/v1/views/home/summary?period=2025-10"

# Con moneda
curl "http://127.0.0.1:8000/api/v1/views/home/summary?period=2025-10&moneda=ARS"

# Sin period -> 422 (FastAPI valida query obligatorio)
curl "http://127.0.0.1:8000/api/v1/views/home/summary"
```

## Fuentes de datos (Sheets)

- **Movimientos** (worksheet "Movimientos de Gastos Personales"): `Fecha`, `Tipo de Movimiento`, `Monto`, `Moneda`, `Id_usuario`
- **Presupuesto** (worksheet "Presupuesto"): `mesAño`, `Monto`

El campo `mesAño` en Presupuesto puede estar en formatos como `YYYY-MM`, `MM/YYYY` o `MM/YY`; se normaliza internamente para comparar con `period`.
