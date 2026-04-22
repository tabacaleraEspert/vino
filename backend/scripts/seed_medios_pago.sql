-- Seed: Catálogo de medios de pago
-- Ejecutar contra la DB Azure SQL Server

-- 1. Tabla de tipos de financiamiento (Credito / Debito)
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'md_card_funding_type')
BEGIN
    CREATE TABLE dbo.md_card_funding_type (
        card_funding_type_id INT IDENTITY(1,1) PRIMARY KEY,
        name NVARCHAR(50) NOT NULL
    );
END;

-- Limpiar e insertar
DELETE FROM dbo.md_card_funding_type;
SET IDENTITY_INSERT dbo.md_card_funding_type ON;
INSERT INTO dbo.md_card_funding_type (card_funding_type_id, name) VALUES
    (1, 'Credito'),
    (2, 'Debito');
SET IDENTITY_INSERT dbo.md_card_funding_type OFF;


-- 2. Tabla de catálogo de medios de pago
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'md_payment_method_catalog')
BEGIN
    CREATE TABLE dbo.md_payment_method_catalog (
        id_medio_de_pago_final INT IDENTITY(1,1) PRIMARY KEY,
        card_funding_type_id INT NULL REFERENCES dbo.md_card_funding_type(card_funding_type_id),
        medio_de_pago_final NVARCHAR(150) NOT NULL,
        is_active BIT NOT NULL DEFAULT 1
    );
END;

-- Limpiar e insertar
DELETE FROM dbo.md_payment_method_catalog;
SET IDENTITY_INSERT dbo.md_payment_method_catalog ON;
INSERT INTO dbo.md_payment_method_catalog (id_medio_de_pago_final, card_funding_type_id, medio_de_pago_final, is_active) VALUES
    -- Efectivo
    (1,  NULL, 'Efectivo', 1),

    -- Tarjeta genérica (sin banco)
    (2,  1,    'Tarjeta - Amex - Credito', 1),

    -- Mercado Pago
    (3,  NULL, 'Mercado Pago - Cuenta - Caja de Ahorro', 1),

    -- BBVA Cuentas
    (4,  NULL, 'BBVA - Cuenta - Caja de Ahorro', 1),
    (5,  NULL, 'BBVA - Cuenta - Cuenta Corriente', 1),

    -- BBVA Tarjetas
    (6,  2,    'BBVA - Tarjeta - Visa - Debito', 1),
    (7,  2,    'BBVA - Tarjeta - Master - Debito', 1),
    (8,  1,    'BBVA - Tarjeta - Visa - Credito', 1),
    (9,  1,    'BBVA - Tarjeta - Master - Credito', 1),
    (10, 1,    'BBVA - Tarjeta - Amex - Credito', 1),

    -- Santander Cuentas
    (11, NULL, 'Santander - Cuenta - Caja de Ahorro', 1),
    (12, NULL, 'Santander - Cuenta - Cuenta Corriente', 1),

    -- Santander Tarjetas
    (13, 2,    'Santander - Tarjeta - Visa - Debito', 1),
    (14, 2,    'Santander - Tarjeta - Master - Debito', 1),
    (15, 1,    'Santander - Tarjeta - Visa - Credito', 1),
    (16, 1,    'Santander - Tarjeta - Master - Credito', 1),
    (17, 1,    'Santander - Tarjeta - Amex - Credito', 1);

SET IDENTITY_INSERT dbo.md_payment_method_catalog OFF;

-- Verificar
SELECT cft.name AS credito_debito,
       cat.medio_de_pago_final,
       cft.card_funding_type_id AS id_credito_debito,
       cat.id_medio_de_pago_final
FROM dbo.md_payment_method_catalog cat
LEFT JOIN dbo.md_card_funding_type cft
    ON cft.card_funding_type_id = cat.card_funding_type_id
WHERE cat.is_active = 1
ORDER BY cat.id_medio_de_pago_final;
