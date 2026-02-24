-- ============================================================
-- ComercioId y CategoriaManual en movimientos
-- ComercioId: referencia al comercio (mer_xxx o comercio-NAME)
-- CategoriaManual: 1 = usuario asignó cat/subcat manualmente (prioridad)
--                  0 = usar cat/subcat del comercio (regla) si existe
-- ============================================================

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.movimientos') AND name = 'ComercioId')
BEGIN
  ALTER TABLE dbo.movimientos ADD ComercioId NVARCHAR(120) NULL;
  PRINT 'Columna ComercioId agregada.';
END

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.movimientos') AND name = 'CategoriaManual')
BEGIN
  ALTER TABLE dbo.movimientos ADD CategoriaManual BIT NOT NULL DEFAULT 0;
  PRINT 'Columna CategoriaManual agregada.';
END
