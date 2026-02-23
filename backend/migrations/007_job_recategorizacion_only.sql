-- ============================================================
-- Solo tabla JobRecategorizacion (si 006 no se ejecutó completa)
-- Requiere: dbo.MaestroUsuarios, dbo.ReglaComercio
-- ============================================================

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'JobRecategorizacion' AND schema_id = SCHEMA_ID('dbo'))
BEGIN
  CREATE TABLE dbo.JobRecategorizacion (
    Id               INT IDENTITY(1,1) PRIMARY KEY,
    Id_usuario       INT NOT NULL,
    ReglaComercioId  INT NOT NULL,
    SinceDate        DATE NOT NULL,
    Status           NVARCHAR(20) NOT NULL DEFAULT N'PENDING',
    UpdatedRows      INT NOT NULL DEFAULT 0,
    Error            NVARCHAR(2000) NULL,
    CreatedAt        DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    UpdatedAt        DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT FK_JobRecategorizacion_Usuario
      FOREIGN KEY (Id_usuario) REFERENCES dbo.MaestroUsuarios(id),
    CONSTRAINT FK_JobRecategorizacion_Regla
      FOREIGN KEY (ReglaComercioId) REFERENCES dbo.ReglaComercio(Id)
  );

  CREATE INDEX IX_JobRecategorizacion_User_Status
  ON dbo.JobRecategorizacion (Id_usuario, Status, CreatedAt DESC);

  PRINT 'Tabla dbo.JobRecategorizacion creada.';
END
ELSE
  PRINT 'Tabla dbo.JobRecategorizacion ya existe.';
