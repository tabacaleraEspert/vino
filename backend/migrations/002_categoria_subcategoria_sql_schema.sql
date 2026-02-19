-- ============================================================
-- Esquema esperado para Categoria y SubCategoria (Azure SQL)
-- Usado por app/db/catalog.py para lectura multi-tenant
-- ============================================================
-- Si las tablas ya existen y están pobladas, verificar que tengan estas columnas.
-- Índices sugeridos para performance:
--   CREATE INDEX IX_Categoria_Id_usuario ON dbo.Categoria (Id_usuario);
--   CREATE INDEX IX_SubCategoria_Id_usuario ON dbo.SubCategoria (Id_usuario);
--   CREATE INDEX IX_SubCategoria_Id_Categoria ON dbo.SubCategoria (Id_Categoria);
-- ============================================================

/*
-- Categoria (si no existe)
CREATE TABLE dbo.Categoria (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    Id_usuario INT NOT NULL,
    Nombre NVARCHAR(200) NOT NULL,
    Icon NVARCHAR(50) NULL DEFAULT '📁',
    Color NVARCHAR(20) NULL DEFAULT '#6b7280',
    [Timestamp] DATETIME2 NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_Categoria_Usuario FOREIGN KEY (Id_usuario) REFERENCES dbo.MaestroUsuarios(id)
);
CREATE INDEX IX_Categoria_Id_usuario ON dbo.Categoria (Id_usuario);

-- SubCategoria (si no existe)
CREATE TABLE dbo.SubCategoria (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    Id_usuario INT NOT NULL,
    Id_Categoria INT NOT NULL,
    Nombre_SubCategoria NVARCHAR(200) NOT NULL,
    [Timestamp] DATETIME2 NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_SubCategoria_Usuario FOREIGN KEY (Id_usuario) REFERENCES dbo.MaestroUsuarios(id),
    CONSTRAINT FK_SubCategoria_Categoria FOREIGN KEY (Id_Categoria) REFERENCES dbo.Categoria(Id)
);
CREATE INDEX IX_SubCategoria_Id_usuario ON dbo.SubCategoria (Id_usuario);
CREATE INDEX IX_SubCategoria_Id_Categoria ON dbo.SubCategoria (Id_Categoria);
*/
