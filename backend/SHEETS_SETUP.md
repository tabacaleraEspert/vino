# Configuración de Google Sheets para Categorías

Para que el CRUD de categorías y subcategorías funcione, las hojas deben tener estas columnas:

## Hoja "Categoria"

| Columna   | Descripción                          |
|-----------|--------------------------------------|
| Id        | Generado por la hoja (ej. fórmula)   |
| Nombre    | Nombre de la categoría                |
| Icon      | Emoji (ej. 🍔, 📁)                    |
| Color     | Hex (ej. #6b7280)                    |
| Timestamp | Para correlación en POST (ISO)       |

**Pasos:** En la hoja Categoria, agregar las columnas **Icon**, **Color** y **Timestamp** después de Nombre (si no existen).

## Hoja "Sub-Categoria"

| Columna          | Descripción                        |
|------------------|------------------------------------|
| Id_Categoria     | ID de la categoría padre            |
| Id               | Generado por la hoja               |
| Nombre_SubCategoria | Nombre de la subcategoría        |
| Timestamp        | Para correlación en POST           |

**Pasos:** En la hoja Sub-Categoria, agregar la columna **Timestamp** (si no existe).

## Hoja "Reglas"

| Columna           | Descripción                          |
|-------------------|--------------------------------------|
| Id                | Generado por la hoja                 |
| Comercio          | Nombre o patrón del comercio         |
| IdCategoria       | ID de categoría                      |
| Nombre_Categoria  | Nombre de categoría                  |
| IdSubCategoria    | ID de subcategoría (vacío si general)|
| Nombre_SubCategoria | Nombre de subcategoría             |
| Timestamp         | Para correlación en POST             |

**Pasos:** En la hoja Reglas, agregar la columna **Timestamp** (si no existe).

## Hoja "Presupuesto"

| Columna          | Descripción                                        |
|------------------|----------------------------------------------------|
| Id               | Generado por la hoja                               |
| mesAño           | Período (YYYY-MM o MM/YY)                           |
| idCategoria      | ID de la categoría                                 |
| Nombre_Categoria | Nombre de la categoría                              |
| idSubcategoria   | ID de subcategoría (vacío = toda la categoría)      |
| Nombre_SubCategoria | Nombre de subcategoría (vacío si general)       |
| Monto            | Monto del presupuesto                              |
| Timestamp        | Para correlación en POST                            |

**Pasos:** En la hoja Presupuesto, agregar la columna **Timestamp** (si no existe).
