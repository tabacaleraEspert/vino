# CLAUDE.md — Vino (Finanzas Personales)

## Qué es este proyecto

App full-stack de finanzas personales. Permite registrar gastos/ingresos, categorizarlos, asignar presupuestos mensuales y definir reglas de auto-categorización por comercio. Multi-usuario con JWT. Desplegado en Azure.

## Stack

- **Backend:** Python 3 · FastAPI 0.115 · SQLAlchemy 2.0 (async, aioodbc) · Azure SQL Server
- **Frontend:** React 18 · React Router 7 · Vite 6 · Tailwind CSS 4 · Radix UI / shadcn · Recharts
- **Auth:** JWT (PyJWT) + bcrypt · token en localStorage (`finanzas_token`)
- **Deploy:** Azure Static Web Apps (frontend) + Azure App Service (backend)

## Estructura del proyecto

```
backend/
  app/
    api/v1/          # Endpoints: auth, movimientos, categorias, subcategorias,
                     #   comercios, reglas, presupuestos, bootstrap, health, admin, views
    core/            # config.py (Settings), security.py (JWT/bcrypt), logging.py
    models/          # ORM: user, movimiento_orm, categoria, subcategoria,
                     #   regla_comercio, presupuesto, job_recategorizacion
    repositories/    # Data access: movimiento_repo, categoria_repo, presupuesto_repo,
                     #   regla_repo, user_repo
    services/        # Business logic
    middleware/      # error_handler, metrics
    cache/           # Catálogo cache con TTL
    db/              # session.py (async engine, pool)
    deps.py          # Dependency injection (get_db, get_current_user)
    main.py          # App init, lifespan, middleware, router mount
  migrations/        # Alembic
  requirements.txt
  .env               # Variables de entorno (SQL_*, JWT_*, MASTER_KEY)

frontend/
  src/
    app/
      components/    # Dashboard, Transactions, Categories, Budgets, Merchants,
                     #   MerchantDetail, Stats, Login, RootLayout, ProtectedRoute,
                     #   modales de creación/edición
      context/       # AuthContext, DataContext, CatalogContext, MonthContext
      routes.tsx     # React Router config
      App.tsx
    lib/
      api.ts         # Tipos TypeScript + mappers backend↔frontend
      api/client.ts  # HTTP client con JWT automático
      dataLayer.ts   # fetchBootstrap(), fetchMovimientos(), cache
    styles/
  vite.config.ts     # Proxy /api → localhost:8000, alias @ → src/
  package.json
```

## Comandos de desarrollo

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev          # Vite en :5173, proxy /api → :8000
npm run build        # Build a dist/
```

## Base de datos

- Azure SQL Server (`mssql+aioodbc://`), ODBC Driver 18
- Pool: size=20, max_overflow=30, recycle=1800s
- Config en `backend/.env`: SQL_SERVER, SQL_DB, SQL_USER, SQL_PASSWORD
- Tablas principales: MaestroUsuarios, movimientos, Categoria, SubCategoria, ReglaComercio, Presupuesto

## API

- Base: `/api/v1`
- Auth: Bearer token en header `Authorization`
- Endpoints principales:
  - `POST /auth/login`, `POST /auth/register`, `GET /auth/me`
  - `GET /bootstrap` — carga catálogo completo (categorías, subcategorías, reglas, presupuestos, comercios) en 1 request
  - `GET|POST|PATCH|DELETE /movimientos`
  - `GET|POST|PATCH|DELETE /categorias`, `/subcategorias`, `/comercios`, `/reglas`, `/presupuestos`
  - `GET /views/home/summary`, `/views/home/breakdown`
  - `GET /health`
- Paginación: `?page=1&limit=50` → `{ items, page, limit, total }`
- Filtros movimientos: `?period=YYYY-MM&tipo=Gasto|Ingreso&categoria_id=N`

## Patrones y convenciones

- **Idioma del dominio:** español (nombres de tablas, campos, endpoints, UI)
- **Arquitectura backend:** Repository pattern → Services → Endpoints
- **Estado frontend:** Context API (no Redux). 4 contextos: Auth, Data, Catalog, Month
- **Bootstrap único:** El frontend carga todo el catálogo en 1 request al iniciar, luego movimientos por mes
- **Formato fechas:** Backend DD/MM/YYYY ↔ Frontend YYYY-MM-DD (mappers en `lib/api.ts`)
- **Errores:** Middleware centralizado, nunca se filtran detalles internos
- **Imports frontend:** Alias `@/` apunta a `src/`

## Flujo n8n — Ingesta automática de gastos desde email

El sistema tiene un flujo externo en n8n que escribe directamente a la misma DB (Azure SQL Server). Este flujo es la fuente principal de datos de gastos.

### Pipeline

```
Gmail triggers (cada minuto, 4 cuentas)
  → GPT-4.1-mini extrae datos del email (fecha, monto, comercio, moneda, descripción)
    → Busca usuario en MaestroUsuarios por gmail
      → Normaliza medio de pago contra md_payment_method_catalog
        → Matchea comercio contra ReglaComercio (contains sobre PatronNorm)
          → SI match: INSERT Movimientos con categoría de la regla + WhatsApp confirmación
          → NO match: INSERT Movimientos como "Otros/Gastos no categorizados" (cat 6, subcat 42)
                      + INSERT nueva ReglaComercio + WhatsApp aviso
```

### Triggers Gmail configurados

| Cuenta | Bancos/Subjects monitoreados |
|--------|------------------------------|
| DV (Davor) | Santander: "Pagaste", "Aviso de transferencia" |
| MM | Macro: "Aviso de compra", Santander |
| IM (Ignacio) | BBVA: "Nueva compra", "Compra aprobada", "Realizaste una transferencia"; MercadoPago: "Pago aprobado en", "Tu transferencia fue enviada" |
| Loli | BBVA, MercadoPago (similar a IM) |

### Tablas que usa n8n (además de las del app)

- `md_payment_method_catalog` — catálogo de medios de pago (crédito/débito + medio final)
- `md_card_funding_type` — tipos de financiamiento (crédito, débito)

### Campos que n8n escribe en Movimientos

`Id_usuario`, `Fecha`, `Timestamp`, `MedioCarga` ('Gmail'), `TipoMovimiento`, `Moneda`, `Monto`, `Id_Credito_Debito`, `Id_Medio_Pago_Final`, `Descripcion`, `Id_Categoria`, `Id_SubCategoria`, `Origen` ('Gmail'), `Origen_Id`, `ComercioRaw`, `ComercioNorm`, `ReglaComercioId`

### Notificaciones

- WhatsApp vía Twilio (templates con ContentSid)
- Notifica confirmación de gasto categorizado o aviso de gasto sin categorizar

### Implicaciones para el desarrollo

- Los movimientos pueden venir del app (manual) o de n8n (automático) — ambos escriben a la misma tabla
- Al modificar la tabla Movimientos o ReglaComercio, considerar que n8n también depende del schema
- El campo `MedioCarga` distingue origen: 'Gmail' (n8n) vs otros (app)
- Categoría "Otros" (id=6) / subcategoría "Gastos no categorizados" (id=42) son los defaults para gastos sin regla

## Notas importantes

- No hay tests todavía (ni backend ni frontend)
- El `.env` del backend tiene credenciales reales — no commitear cambios a ese archivo sin cuidado
- CORS configurado para localhost:5173-5175 y Azure Static Apps
- Compresión GZip habilitada (min 500 bytes)
