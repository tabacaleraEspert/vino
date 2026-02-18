# Login con Azure SQL

## Resumen

- **Login**: usuario (Nombre) + contraseña
- **BD**: Azure SQL, tabla `MaestroUsuarios` con columna `PasswordHash`
- **Sheets**: cada usuario tiene `ID_Sheets` → su Google Sheet propio
- **JWT**: incluye `id_sheets` para que el backend use el Sheet correcto

## 1. SQL: agregar columna PasswordHash

Ejecutar en Azure SQL:

```sql
ALTER TABLE MaestroUsuarios ADD PasswordHash NVARCHAR(255) NULL;
CREATE INDEX IX_MaestroUsuarios_Nombre ON MaestroUsuarios (Nombre);
```

Ver `migrations/001_add_password_to_usuarios.sql` para el script completo.

## 2. Variables de entorno (.env)

```env
SQL_SERVER=tu-servidor.database.windows.net
SQL_DB=tu_base_de_datos
SQL_USER=tu_usuario
SQL_PASSWORD=tu_contraseña
SQL_USUARIO_TABLE=MaestroUsuarios   # opcional, default "MaestroUsuarios"
```

## 3. Setear password inicial

```bash
cd backend
python -m scripts.set_password Davor miPassword123
```

## 4. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"Davor","password":"miPassword123"}'
```

Respuesta:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": "1",
    "nombre": "Davor",
    "apellido": "Vindis",
    "gmail": "davor.vindis99@gmail.com"
  }
}
```

## 5. Rutas protegidas

Todas las rutas de datos (movimientos, categorías, reglas, presupuestos, views, comercios) requieren:

```
Authorization: Bearer <access_token>
```

El backend usa `id_sheets` del token para acceder al Google Sheet del usuario.
