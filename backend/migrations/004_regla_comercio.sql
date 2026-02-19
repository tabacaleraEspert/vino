-- ============================================================
-- Tabla dbo.ReglaComercio - Reglas de categorización por comercio
-- Matching CONTAINS sobre razón social (merchant descriptor)
-- ============================================================

CREATE TABLE dbo.ReglaComercio (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    Id_usuario INT NOT NULL,
    Patron NVARCHAR(120) NOT NULL,
    PatronNorm NVARCHAR(120) NOT NULL,
    EjemploRazonSocial NVARCHAR(300) NULL,
    Id_Categoria INT NOT NULL,
    Id_SubCategoria INT NOT NULL,
    Prioridad INT NOT NULL DEFAULT 100,
    Activa BIT NOT NULL DEFAULT 1,
    Confianza NVARCHAR(20) NOT NULL DEFAULT 'AUTO',
    CreadoEn DATETIME2 DEFAULT SYSUTCDATETIME(),
    ActualizadoEn DATETIME2 DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_ReglaComercio_Usuario FOREIGN KEY (Id_usuario) REFERENCES dbo.MaestroUsuarios(id),
    CONSTRAINT FK_ReglaComercio_Categoria FOREIGN KEY (Id_Categoria) REFERENCES dbo.Categoria(Id),
    CONSTRAINT FK_ReglaComercio_SubCategoria FOREIGN KEY (Id_SubCategoria) REFERENCES dbo.SubCategoria(Id),
    CONSTRAINT UQ_ReglaComercio_Usuario_PatronNorm UNIQUE (Id_usuario, PatronNorm)
);

CREATE INDEX IX_ReglaComercio_Id_usuario ON dbo.ReglaComercio (Id_usuario);
CREATE INDEX IX_ReglaComercio_Activa ON dbo.ReglaComercio (Id_usuario, Activa);
