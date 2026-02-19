-- ============================================================
-- Recategorización automática: ReglaComercioId en movimientos + JobRecategorizacion
-- ============================================================

-- A) Alter tabla movimientos: referencia a regla aplicada
ALTER TABLE dbo.movimientos
ADD ReglaComercioId INT NULL,
    ComercioRaw NVARCHAR(300) NULL,
    ComercioNorm NVARCHAR(300) NULL;

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_movimientos_ReglaComercio')
BEGIN
  ALTER TABLE dbo.movimientos
  ADD CONSTRAINT FK_movimientos_ReglaComercio
    FOREIGN KEY (ReglaComercioId) REFERENCES dbo.ReglaComercio(Id);
END

CREATE INDEX IX_movimientos_User_Regla_Fecha
ON dbo.movimientos (Id_usuario, ReglaComercioId, Fecha DESC)
WHERE ReglaComercioId IS NOT NULL;

-- IX_movimientos_User_Fecha ya existe; si no:
-- CREATE INDEX IX_movimientos_User_Fecha ON dbo.movimientos (Id_usuario, Fecha DESC);

-- B) Tabla JobRecategorizacion (auditoría y retries)
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
