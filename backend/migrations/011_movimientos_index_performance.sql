-- ============================================================
-- Índices para mejorar performance de summary, breakdown y movimientos
-- ============================================================

-- Índice compuesto para queries por usuario + tipo + rango de fechas
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_movimientos_Id_usuario_Tipo_Fecha' AND object_id = OBJECT_ID('dbo.movimientos'))
BEGIN
  CREATE INDEX IX_movimientos_Id_usuario_Tipo_Fecha
    ON dbo.movimientos (Id_usuario, TipoMovimiento, Fecha DESC);
  PRINT 'Índice IX_movimientos_Id_usuario_Tipo_Fecha creado.';
END
