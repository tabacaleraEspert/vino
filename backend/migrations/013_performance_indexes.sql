-- ============================================================
-- 013: Índices de performance para queries mobile-first
-- Cubre: movimientos (fecha+categoria), ReglaComercio (patron),
--         Categoria, SubCategoria (multi-tenant)
-- ============================================================

-- 1. movimientos: covering index para listados con Fecha DESC + columnas frecuentes
--    Reemplaza IX_movimientos_Fecha que no incluye columnas de proyección
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_mov_user_fecha_cover' AND object_id = OBJECT_ID('dbo.movimientos'))
BEGIN
  CREATE INDEX IX_mov_user_fecha_cover
    ON dbo.movimientos (Id_usuario, Fecha DESC)
    INCLUDE (Monto, TipoMovimiento, Id_Categoria, Id_SubCategoria, ComercioId, Descripcion);
  PRINT 'IX_mov_user_fecha_cover creado.';
END

-- 2. movimientos: para dashboard agrupado por categoría
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_mov_user_cat' AND object_id = OBJECT_ID('dbo.movimientos'))
BEGIN
  CREATE INDEX IX_mov_user_cat
    ON dbo.movimientos (Id_usuario, Id_Categoria)
    INCLUDE (Monto, TipoMovimiento, Fecha);
  PRINT 'IX_mov_user_cat creado.';
END

-- 3. ReglaComercio: lookup por patrón normalizado (solo activas)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_regla_user_patron_activa' AND object_id = OBJECT_ID('dbo.ReglaComercio'))
BEGIN
  CREATE INDEX IX_regla_user_patron_activa
    ON dbo.ReglaComercio (Id_usuario, PatronNorm)
    INCLUDE (Id_Categoria, Id_SubCategoria, Prioridad)
    WHERE Activa = 1;
  PRINT 'IX_regla_user_patron_activa creado.';
END

-- 4. Categoria: multi-tenant lookup
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_cat_user' AND object_id = OBJECT_ID('dbo.Categoria'))
BEGIN
  CREATE INDEX IX_cat_user
    ON dbo.Categoria (Id_usuario)
    INCLUDE (Nombre, Icon, Color);
  PRINT 'IX_cat_user creado.';
END

-- 5. SubCategoria: multi-tenant + filtro por categoría padre
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_subcat_user_cat' AND object_id = OBJECT_ID('dbo.SubCategoria'))
BEGIN
  CREATE INDEX IX_subcat_user_cat
    ON dbo.SubCategoria (Id_usuario, Id_Categoria)
    INCLUDE (Nombre_SubCategoria);
  PRINT 'IX_subcat_user_cat creado.';
END

-- 6. Presupuesto: lookup por usuario + periodo
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_pres_user_mes' AND object_id = OBJECT_ID('dbo.Presupuestos'))
BEGIN
  CREATE INDEX IX_pres_user_mes
    ON dbo.Presupuestos (Id_usuario, MesAnio)
    INCLUDE (Id_Categoria, Id_SubCategoria, Monto);
  PRINT 'IX_pres_user_mes creado.';
END
