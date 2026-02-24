-- ============================================================
-- Corrige SubCategoria.Id_Categoria cuando apuntan a Categoria.Id
-- que ya no existen (ej: categorías recreadas con nuevos IDs).
-- Mapea por orden: Id_Categoria=1 → 1ª categoría por Nombre, etc.
--
-- Ejecutar en Azure SQL / SSMS. Luego: reiniciar backend o esperar
-- TTL del cache; en frontend pulsar "Actualizar datos".
-- ============================================================

-- Subcategorías huérfanas: Id_Categoria no existe en Categoria para ese usuario
WITH CatPorOrden AS (
  SELECT Id, Id_usuario, Nombre,
    ROW_NUMBER() OVER (PARTITION BY Id_usuario ORDER BY Nombre) AS rn
  FROM dbo.Categoria
),
SubsHuerfanas AS (
  SELECT sc.Id AS sub_id, sc.Id_usuario, sc.Id_Categoria AS old_cat_id
  FROM dbo.SubCategoria sc
  WHERE NOT EXISTS (
    SELECT 1 FROM dbo.Categoria c
    WHERE c.Id = sc.Id_Categoria AND c.Id_usuario = sc.Id_usuario
  )
)
UPDATE sc
SET sc.Id_Categoria = co.Id,
    sc.[Timestamp] = SYSUTCDATETIME()
FROM dbo.SubCategoria sc
INNER JOIN SubsHuerfanas sh ON sh.sub_id = sc.Id AND sh.Id_usuario = sc.Id_usuario
INNER JOIN CatPorOrden co ON co.Id_usuario = sc.Id_usuario AND co.rn = sc.Id_Categoria;
