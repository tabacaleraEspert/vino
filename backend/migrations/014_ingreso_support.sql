-- 014: Soporte de Ingresos
-- Agrega columna Tipo a Categoria y TipoMovimiento a ReglaComercio
-- Seed de categorias de ingreso para todos los usuarios existentes

-- 1. Columnas nuevas
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('Categoria') AND name = 'Tipo'
)
BEGIN
    ALTER TABLE Categoria ADD Tipo NVARCHAR(20) NOT NULL DEFAULT 'Gasto';
END

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('ReglaComercio') AND name = 'TipoMovimiento'
)
BEGIN
    ALTER TABLE ReglaComercio ADD TipoMovimiento NVARCHAR(20) NOT NULL DEFAULT 'Gasto';
END
GO

-- 2. Marcar categorías "Ingresos" existentes como tipo Ingreso
UPDATE Categoria SET Tipo = 'Ingreso' WHERE Nombre = 'Ingresos' AND Tipo = 'Gasto';
GO

-- 3. Seed para usuarios que NO tienen categoría "Ingresos"
DECLARE @uid INT;
DECLARE @cat_id INT;

DECLARE user_cursor CURSOR FOR
    SELECT id FROM MaestroUsuarios
    WHERE id NOT IN (SELECT Id_usuario FROM Categoria WHERE Nombre = 'Ingresos');

OPEN user_cursor;
FETCH NEXT FROM user_cursor INTO @uid;

WHILE @@FETCH_STATUS = 0
BEGIN
    INSERT INTO Categoria (Id_usuario, Nombre, Icon, Color, Bucket, Tipo)
    VALUES (@uid, 'Ingresos', N'💰', '#22c55e', NULL, 'Ingreso');

    SET @cat_id = SCOPE_IDENTITY();

    INSERT INTO SubCategoria (Id_usuario, Id_Categoria, Nombre_SubCategoria) VALUES
        (@uid, @cat_id, 'Sueldo'),
        (@uid, @cat_id, 'Freelance'),
        (@uid, @cat_id, 'Inversiones'),
        (@uid, @cat_id, 'Ventas'),
        (@uid, @cat_id, 'Reembolsos'),
        (@uid, @cat_id, 'Ingresos no categorizados');

    FETCH NEXT FROM user_cursor INTO @uid;
END

CLOSE user_cursor;
DEALLOCATE user_cursor;
GO

-- 4. Agregar subcategorías faltantes a categorías "Ingresos" que ya existían pero sin subs
INSERT INTO SubCategoria (Id_usuario, Id_Categoria, Nombre_SubCategoria)
SELECT c.Id_usuario, c.Id, v.nombre
FROM Categoria c
CROSS APPLY (VALUES ('Sueldo'),('Freelance'),('Inversiones'),('Ventas'),('Reembolsos'),('Ingresos no categorizados')) v(nombre)
WHERE c.Nombre = 'Ingresos' AND c.Tipo = 'Ingreso'
AND NOT EXISTS (
    SELECT 1 FROM SubCategoria s
    WHERE s.Id_usuario = c.Id_usuario AND s.Id_Categoria = c.Id AND s.Nombre_SubCategoria = v.nombre
);
