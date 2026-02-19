-- ============================================================
-- Tabla dbo.Presupuestos para presupuestos multi-tenant
-- ============================================================
-- Ejecutar en Azure SQL Database
-- ============================================================

CREATE TABLE dbo.Presupuestos (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    Id_usuario INT NOT NULL,
    PeriodoMes DATE NOT NULL,
    Id_Categoria INT NULL,
    Id_SubCategoria INT NULL,
    Monto DECIMAL(18,2) NOT NULL,
    [Timestamp] DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_Presupuestos_Usuario FOREIGN KEY (Id_usuario) REFERENCES dbo.MaestroUsuarios(id),
    CONSTRAINT FK_Presupuestos_Categoria FOREIGN KEY (Id_Categoria) REFERENCES dbo.Categoria(Id),
    CONSTRAINT FK_Presupuestos_SubCategoria FOREIGN KEY (Id_SubCategoria) REFERENCES dbo.SubCategoria(Id)
);

CREATE INDEX IX_Presupuestos_Id_usuario ON dbo.Presupuestos (Id_usuario);
CREATE INDEX IX_Presupuestos_PeriodoMes ON dbo.Presupuestos (PeriodoMes);
CREATE INDEX IX_Presupuestos_Id_usuario_PeriodoMes ON dbo.Presupuestos (Id_usuario, PeriodoMes);
