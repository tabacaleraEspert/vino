-- ============================================================
-- Migración: agregar columna PasswordHash a la tabla de usuarios
-- Ejecutar en Azure SQL Database
-- ============================================================
-- Tabla: MaestroUsuarios
-- Este script asume que la tabla ya existe con: id, Nombre, Apellido,
-- WppEntero, Whatsapp, gmail, ID_Sheets, CreatedAt, UpdatedAt

-- 1. Agregar columna PasswordHash (hash bcrypt ~60 caracteres)
ALTER TABLE MaestroUsuarios
ADD PasswordHash NVARCHAR(255) NULL;

-- 2. Índice para búsqueda rápida por Nombre en login
CREATE INDEX IX_MaestroUsuarios_Nombre ON MaestroUsuarios (Nombre);

-- ============================================================
-- Script alternativo: crear tabla desde cero (si no existe)
-- ============================================================
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
*/

-- ============================================================
-- Para setear password desde la app (Python):
--   import bcrypt
--   pwd = "miPassword123"
--   hashed = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
--   UPDATE MaestroUsuarios SET PasswordHash = ? WHERE Nombre = 'Davor';
