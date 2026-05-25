-- Migration 015: Add Apodo column to MaestroUsuarios
ALTER TABLE MaestroUsuarios ADD Apodo NVARCHAR(50) NULL;
