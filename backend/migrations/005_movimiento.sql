-- ============================================================
-- Tabla dbo.movimientos - Gastos/Ingresos (multi-tenant por Id_usuario)
-- Reemplaza Google Sheets para movimientos.
-- ============================================================

CREATE TABLE dbo.movimientos (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    Id_usuario INT NOT NULL,
    Fecha DATE NOT NULL,
    [Timestamp] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    MedioCarga NVARCHAR(30) NOT NULL,
    TipoMovimiento NVARCHAR(20) NOT NULL,
    Moneda NVARCHAR(10) NOT NULL,
    Monto DECIMAL(18,2) NOT NULL,
    Id_Credito_Debito INT NULL,
    Id_Medio_Pago_Final INT NULL,
    Descripcion NVARCHAR(500) NULL,
    Id_Categoria INT NULL,
    Id_SubCategoria INT NULL,
    Origen NVARCHAR(50) NULL,
    Origen_Id NVARCHAR(120) NULL,
    CONSTRAINT FK_movimientos_Usuario FOREIGN KEY (Id_usuario) REFERENCES dbo.MaestroUsuarios(id),
    CONSTRAINT FK_movimientos_Categoria FOREIGN KEY (Id_Categoria) REFERENCES dbo.Categoria(Id),
    CONSTRAINT FK_movimientos_SubCategoria FOREIGN KEY (Id_SubCategoria) REFERENCES dbo.SubCategoria(Id),
    CONSTRAINT CK_movimientos_Tipo CHECK (TipoMovimiento IN ('Gasto','Ingreso')),
    CONSTRAINT CK_movimientos_Monto CHECK (Monto >= 0)
);

CREATE INDEX IX_movimientos_Id_usuario ON dbo.movimientos (Id_usuario);
CREATE INDEX IX_movimientos_Fecha ON dbo.movimientos (Id_usuario, Fecha);
CREATE INDEX IX_movimientos_Origen ON dbo.movimientos (Id_usuario, Origen, Origen_Id);
