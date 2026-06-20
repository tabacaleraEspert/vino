# CLAUDE.md — Fina (Finanzas Personales)

## Qué es este proyecto

App full-stack de finanzas personales. Permite registrar gastos/ingresos automáticamente desde Gmail, categorizarlos, asignar presupuestos mensuales y consultar/registrar gastos vía WhatsApp. Multi-usuario con JWT.

## Stack actual

- **Backend:** Python 3 · FastAPI 0.115 · SQLAlchemy 2.0 async · **Neon PostgreSQL** (asyncpg)
- **Frontend:** React 18 · React Router 7 · Vite 6 · Tailwind CSS 4 · Radix UI / shadcn · PWA
- **Auth:** JWT (PyJWT, 30 días) + bcrypt · Google OAuth · Apple Sign-In
- **IA:** OpenAI GPT-4.1-mini (extracción, clasificación, queries) · Whisper (audio WA)
- **WhatsApp:** Twilio Sandbox (+1 570 909-1218)
- **Deploy:** Firebase Hosting (frontend) · Google Cloud Run (backend)
- **GCP:** Proyecto `ahorro-app-498519` · Servicio `ahorros-backend` · Región `us-central1`

## URLs de producción

- **Frontend:** https://ahorros-app-46e0e.web.app
- **Backend:** https://ahorros-backend-243397640627.us-central1.run.app
- **DB:** Neon PostgreSQL (ver DATABASE_URL en .env)

## Estructura del proyecto

```
backend/
  app/
    api/v1/          # auth, movimientos, categorias, subcategorias,
                     # comercios, reglas, presupuestos, bootstrap,
                     # health, admin, gmail, whatsapp, ingest, views
    core/            # config.py (Settings), security.py (JWT/bcrypt)
    models/          # ORM: user, movimiento_orm, categoria, etc.
    repositories/    # Data access layer
    services/        # Business logic:
                     #   gmail_poller.py — polling Gmail cada ~90s
                     #   email_expense_extractor.py — GPT extrae datos de emails
                     #   expense_extractor.py — GPT extrae datos de mensajes WA
                     #   whatsapp_intake.py — clasifica intent WA (DATA/QUERY/etc.)
                     #   query_parser/executor/formatter — responde preguntas financieras
                     #   twilio_client.py — envía mensajes WA
                     #   purchase_advisor.py — "¿puedo comprar X?"
                     #   ticket_reader.py — OCR de fotos de tickets
    middleware/      # error_handler, metrics
    db/              # session.py (async engine, pool)
    deps.py          # Dependency injection
    main.py          # App init, lifespan, routers
  .env               # Credenciales reales — NO commitear

frontend/
  src/
    app/
      components/fina/   # Todas las pantallas y sheets de la app
      context/           # AuthContext, DataContext, CatalogContext, MonthContext
      routes.tsx
    lib/
      api.ts             # Tipos TypeScript + mappers backend↔frontend
      dataLayer.ts       # fetchBootstrap(), fetchMovimientos(), cache
  vite.config.ts         # Proxy /api → localhost:8000
```

## Comandos de desarrollo

```bash
# Backend
cd backend
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev          # Vite en :5173, proxy /api → :8000
npm run build        # Build a dist/
firebase deploy      # Deploy frontend a Firebase
```

## Deploy backend

```bash
gcloud run deploy ahorros-backend --source . --region=us-central1 --project=ahorro-app-498519 --quiet
```

## Base de datos

- **Neon PostgreSQL** (serverless, cloud)
- Config en `.env`: `DATABASE_URL=postgresql+asyncpg://...`
- Tablas principales: `MaestroUsuarios`, `movimientos`, `Categoria`, `SubCategoria`, `ReglaComercio`, `Presupuesto`
- Google Sheets: **ya no se usa** — todo migrado a Postgres

## Flujo de ingesta Gmail (reemplazó n8n)

El backend tiene su propio poller interno que corre cada ~90 segundos:

```
gmail_poller.py (cada ~90s por usuario)
  → Busca emails bancarios nuevos (BBVA, MercadoPago, Santander, etc.)
    → GPT extrae: monto, comercio, fecha, tipo, medio_de_pago
      → Busca regla en ReglaComercio para el comercio
        → SI regla existe: asigna categoría de la regla
        → NO existe: asigna "Otros / Gastos no categorizados" (cat 6, subcat 42)
          + crea ReglaComercio con confianza="AUTO" para que el usuario la categorice
      → Crea movimiento en DB
      → Notifica por WhatsApp (freeform — requiere ventana 24h activa)
```

**Usuarios con Gmail conectado:**
- Ignacio (id=11) — ignamedico@gmail.com — BBVA + MercadoPago

**Nota importante:** La categorización con IA fue removida intencionalmente.
Los comercios nuevos van directo a "Otros" para que el usuario los categorice manualmente.
Esto es una decisión de producto — la categorización AI automática es un feature premium futuro.

## Flujo WhatsApp

El webhook en `POST /api/v1/whatsapp/webhook` recibe mensajes de Twilio y:
1. Resuelve usuario por `WppEntero` (formato `whatsapp:+549...`)
2. Detecta comandos (CAMBIAR, CATEGORIZAR, etc.) o clasifica intent con GPT
3. Rutea: DATA → registra gasto | QUERY → responde consulta | SUGERENCIAS → advice | OTHER → conversacional
4. Soporta: texto, audio (Whisper), fotos de tickets (OCR)

**Config Twilio Sandbox:** en Twilio Console → Messaging → Try it out → WhatsApp → Sandbox Settings
URL webhook: `https://ahorros-backend-243397640627.us-central1.run.app/api/v1/whatsapp/webhook`

## API

- Base: `/api/v1`
- Auth: Bearer token en header `Authorization`
- Master Key: header `X-Master-Key` para endpoints admin/internos
- Endpoints clave:
  - `POST /auth/login`, `/auth/register`, `/auth/google`, `/auth/apple`
  - `POST /auth/whatsapp/send-code`, `/auth/whatsapp/verify-code`
  - `GET /bootstrap` — carga catálogo completo en 1 request
  - `GET|POST|PATCH|DELETE /movimientos`
  - `GET|POST|PATCH|DELETE /categorias`, `/subcategorias`, `/comercios`, `/reglas`, `/presupuestos`
  - `POST /gmail/poll` — fuerza re-poll Gmail (admin)
  - `POST /whatsapp/webhook` — webhook Twilio (sin auth)
  - `GET /health`

## Patrones y convenciones

- **Idioma del dominio:** español (tablas, campos, endpoints, UI)
- **Arquitectura backend:** Repository pattern → Services → Endpoints
- **Estado frontend:** Context API (no Redux). 4 contextos: Auth, Data, Catalog, Month
- **JWT:** 30 días de expiración. Se valida en startup del frontend.
- **Categoría default:** "Otros" (id=6) / "Gastos no categorizados" (id=42)
- **Formato fechas:** Backend DD/MM/YYYY ↔ Frontend YYYY-MM-DD
- **WppEntero:** formato `whatsapp:+549XXXXXXXXXX`

## Usuarios activos

| id | Nombre  | Gmail                    | WPP |
|----|---------|--------------------------|-----|
| 11 | Ignacio | ignamedico@gmail.com     | ✅  |
| 12 | Davor   | davor.vindis99@gmail.com | ✅  |

## Notas importantes

- No hay tests todavía (ni backend ni frontend)
- El `.env` del backend tiene credenciales reales — NO commitear
- Twilio Sandbox: notificaciones freeform solo funcionan dentro de ventana 24h
- CORS configurado para localhost:5173-5175, Firebase y Cloud Run
- Google Sheets: removido. El campo `ID_Sheets` en MaestroUsuarios es legacy.
- n8n: removido. El polling Gmail es interno al backend.
