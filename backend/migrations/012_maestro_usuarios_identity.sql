-- ============================================================
-- Migración: convertir id a IDENTITY en MaestroUsuarios
-- Permite INSERT sin especificar id (auto-generado).
-- Ejecutar en Azure SQL Database
-- ============================================================
-- SQL Server no permite ALTER COLUMN para añadir IDENTITY.
-- Hay que recrear la tabla. Hacer backup antes.

-- Paso 1: Backup
SELECT * INTO MaestroUsuarios_backup_20260224 FROM MaestroUsuarios;

-- Paso 2: Dropear FKs que referencian MaestroUsuarios
-- (Categoria, SubCategoria, ReglaComercio, movimientos, Presupuestos, JobRecategorizacion)
-- Ejecutar: SELECT name FROM sys.foreign_keys WHERE referenced_object_id = OBJECT_ID('MaestroUsuarios');

-- Paso 3: Dropear tabla
-- DROP TABLE MaestroUsuarios;

-- Paso 4: Crear tabla con IDENTITY
/*
CREATE TABLE MaestroUsuarios (
    id INT IDENTITY(1,1) PRIMARY KEY,
    Nombre NVARCHAR(100) NOT NULL,
    Apellido NVARCHAR(100),
    WppEntero NVARCHAR(50),
    Whatsapp NVARCHAR(50),
    gmail NVARCHAR(255),
    ID_Sheets NVARCHAR(500),
    PasswordHash NVARCHAR(255),
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2 DEFAULT GETUTCDATE()
);

CREATE INDEX IX_MaestroUsuarios_Nombre ON MaestroUsuarios (Nombre);

SET IDENTITY_INSERT MaestroUsuarios ON;
INSERT INTO MaestroUsuarios (id, Nombre, Apellido, WppEntero, Whatsapp, gmail, ID_Sheets, PasswordHash, CreatedAt, UpdatedAt)
SELECT id, Nombre, Apellido, WppEntero, Whatsapp, gmail, ID_Sheets, PasswordHash, CreatedAt, UpdatedAt
FROM MaestroUsuarios_backup_20260224;
SET IDENTITY_INSERT MaestroUsuarios OFF;
*/

-- Paso 5: Recrear FKs (ver migraciones 002, 004, 005, 006, 007)
